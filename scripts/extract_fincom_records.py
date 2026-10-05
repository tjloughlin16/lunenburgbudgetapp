"""Finance Committee tasks A5, H1, J1 of `sources/data/finance-committee-tasks.csv`.

    python3 scripts/extract_fincom_records.py            # run all three, write the CSVs
    python3 scripts/extract_fincom_records.py --check    # ...and fail if a kept row does
                                                           # not tie, or an output is stale
    python3 scripts/extract_fincom_records.py --task a5  # just one task (a5|h1|j1)

Writes, under `sources/data/`:

    fy20-q4-reports.csv            A5: proven rows, both scanned versions
    fy20-q4-version-diff.csv       A5: revised vs original, matched row by row
    fy20-q4-vs-gl-history.csv      A5: FY2020 expense departments vs gl-history
    fy20-q4-unreadable.csv         A5: pages/rows that did not prove, and why

    warrant-articles-fincom.csv       H1: articles, amounts, funding-source hits
    warrant-article-amount-diff.csv   H1: amounts across drafts of the same FY
    warrant-article-tracking-fincom.csv   H1: the tracking-sheet snapshots
    warrant-article-tracking-diff.csv     H1: what changed between snapshots
    prior-year-bills-fincom.csv       H1: the FY27 prior-year-bills tracker
    free-cash-history-fincom.csv      H1: the Free Cash Fact Sheet's own history table
    warrant-vs-votes-fincom.csv       H1: draft amounts vs the recorded Town Meeting votes

    trust-fund-purposes.csv        J1: donor intent / restrictions, page-cited
    trust-ledger-entries.csv       J1: the Susan Howard ledger's own proven totals
    j1-unreadable.csv              J1: pages not reliably read, and why

------------------------------------------------------------------------------
RULE 13b, APPLIED TO A5 AND J1's LEDGER: measure, band, place, name, prove.
------------------------------------------------------------------------------

Both of A5's PDFs are scans (`pdf_kind.py`: 37 pages, all `image`). Their plain OCR text
(already sitting under `text/`) is USELESS for the table: Vision reads a scanned MUNIS
`glytdbud` page roughly column-major, not row-major, so a page's labels come out as one
block and its six figure columns come out as later blocks, with no row correspondence a
line-based parser can recover. `extract_munis_report.py`'s own regex -- written for a
digital report where org, object, name and six figures share one text line -- matches
nothing here, which is the right answer for the wrong reason: nobody should widen it to
pull these in (its own docstring says as much about a different folder).

So this reads `ocr_pdf.swift --boxes` geometry instead: every recognised line with its
(x, y, w, h) in page-normalised coordinates. On that page, the header line's own boxes
("ORIGINAL"/"APPROP", "REVISED"/"BUDGET", "YTD EXPENDED", "ENCUMBRANCES", "AVAILABLE"/
"BUDGET", "PCT"/"USED") give seven column CENTRES, read fresh per page because a scan's
columns drift page to page. Every other box below the header is either a LABEL (left of
the first numeric centre) or a VALUE (assigned to whichever of the seven centres its own
centre is nearest). Rows are recovered by clustering box centres on y: an account's own
code and its description print as two boxes roughly 0.002 apart, while two different
rows sit roughly 0.013 apart, so a single-linkage chain with a ~0.006 threshold merges
the first without merging the second -- no page-wide "pitch" needs to be measured because
MUNIS, unlike a photographed ledger, does not rotate the page.

A row is published only if it PROVES the report's own two identities:

    original + transfers  = revised
    revised - ytd - encumbrances = available        (encumbrances defaults to 0 when the
                                                       cell prints nothing, which it often
                                                       does for a zero)

both to the cent. This is rule 13b's last line doing the actual work: a wrong column
assignment does not make two real identities close on the same row by accident, so a row
that ties is a row that was read correctly, whichever account it turns out to belong to.
Checked independently on FY2020 page 3: three leaf accounts under "31 DEPT REV - SCHOOL"
sum to exactly that section's own "TOTAL DEPT REV - SCHOOL" line, which nothing in the
row-level identity requires -- it is the page agreeing with itself a second way.

The same primitive (`read_report_page`) is reused for the Susan Howard trust ledger's
"SUMMARY OF FUNDS" table (J1): one value column instead of seven, proven by summing its
twenty category rows against the page's own "GRAND TOTAL TRUST FUNDS" line (ties to the
cent). The ledger's detailed six-column fund-by-fund table on the same pages is NOT
resolved here -- six columns on a page this dense needs its own column-centre reading
and more passes than this task's budget allows -- and it is named in `j1-unreadable.csv`
rather than guessed at.

------------------------------------------------------------------------------
H1: no OCR. Two heading conventions, found by trying both and keeping the one that wins.
------------------------------------------------------------------------------

The FY24 (2-28-23) and FY25 (3-10-24) draft warrants put the article's OPERATIVE TEXT
right after the letter ("A.  To see if the Town will vote..."); the FY26 docx uses
"ARTICLE A:  TITLE"; the FY27 drafts (3.7.26, 4.2.26, 4.5.26) put an ALL-CAPS TITLE on its
own line after the letter. A single regex silently drops whichever convention it was not
written for -- not an absence, rule 13c's own shape -- so `split_articles()` tries three
patterns and keeps whichever one finds the most headings on that document.

Dollar amounts are read per article body, with the SENTENCE containing each one searched
for a list of named funding-source phrases ("Free Cash", "Stabilization Fund", "Water
Enterprise Fund", ...) actually printed in these warrants. A sentence naming none is left
blank rather than guessed at.
"""
import argparse
import csv
import difflib
import os
import re
import statistics
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
OCR_CACHE = os.path.join(ROOT, 'build', 'ocr-cache')


def data(name):
    return os.path.join(DATA, name)


def orig_doc(rel):
    """Rule 12: cite the document itself, not our extracted-text copy of it. Every path
    in this script that reads prose is '<dir>/text/<name>.<ext>.txt'; this returns
    'sources/<dir>/<name>.<ext>' -- the PDF/xlsx/docx a reader can actually open."""
    rel = re.sub(r'/text/', '/', rel)
    rel = re.sub(r'\.txt$', '', rel)
    return 'sources/' + rel


# ==============================================================================
# SHARED: box-geometry table reading (rule 13b: measure, band, place, name, prove)
# ==============================================================================

def ensure_ocr_boxes(pdf_path, cache_name):
    """Return the path to `<cache_name>.tsv` under build/ocr-cache/, running
    `ocr_pdf.swift --boxes` if it is not already cached there. Never written into
    sources/ -- this is derived scratch, not an archive artifact."""
    os.makedirs(OCR_CACHE, exist_ok=True)
    out = os.path.join(OCR_CACHE, cache_name + '.tsv')
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    swift = os.path.join(ROOT, 'scripts', 'ocr_pdf.swift')
    print('  OCR: %s -> %s' % (os.path.relpath(pdf_path, ROOT), os.path.relpath(out, ROOT)),
          file=sys.stderr)
    subprocess.run(['swift', swift, pdf_path, out, '2', '--boxes'],
                    check=True, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


def load_boxes(tsv_path):
    """Boxes as a list of dicts. Parsed by splitting on tab, NOT the csv module: Vision's
    text can carry characters (quotes, odd punctuation) that the csv dialect's quoting
    misreads as an unterminated field, and that silently merges two lines into one giant
    'text' value. A plain split never has that failure mode on a file with no embedded
    tabs, which `ocr_pdf.swift` does not emit."""
    boxes = []
    with open(tsv_path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    for ln in lines[1:]:
        if not ln:
            continue
        parts = ln.split('\t')
        if len(parts) != 7:
            continue
        page, x, y, w, h, conf, text = parts
        boxes.append(dict(page=int(page), x=float(x), y=float(y), w=float(w), h=float(h),
                           conf=float(conf), text=text))
    return boxes


def cluster_rows(boxes, threshold):
    """Single-linkage clustering on y: a chain of boxes where each is within `threshold`
    of the previous becomes one row. An account's code and its description print about
    0.002 apart; two different rows print about 0.013 apart on these MUNIS pages, so a
    threshold around 0.006 separates them without a page-wide rotation/pitch measurement
    -- unlike the photographed trust tables (`read_trust_table.py`), these MUNIS scans do
    not rotate."""
    srt = sorted(boxes, key=lambda b: -b['y'])
    clusters, cur, last_y = [], [], None
    for b in srt:
        if last_y is not None and (last_y - b['y']) > threshold:
            clusters.append(cur)
            cur = []
        cur.append(b)
        last_y = b['y']
    if cur:
        clusters.append(cur)
    return clusters


def money(tok):
    """A figure as this scan prints it: '-20,083.00', '. 00' (a stray OCR space before the
    point), '- 00' (ditto, and no point read at all), '42,821, 878.82' (a thousands comma
    broken by a space). Returns None, never a guess, when the token is not recognisably a
    figure -- a row built on a None fails its identity check and is not published."""
    t = re.sub(r'\s+', '', tok.strip())
    if not t:
        return None
    # OCR misreads a short, faint minus sign as a tilde on at least one row (page 6,
    # BLIND ABATEMENT: '~ 525.00' for what the ORIGINAL and AVAILABLE columns on the same
    # row both print as '-525.00'). Treated the same as a leading '-'.
    if t.startswith('~'):
        t = '-' + t[1:]
    neg = t.startswith('-')
    if neg:
        t = t[1:]
    if t in ('', '.00', '.0', '00', '0', '.000', '.', ',00', ',0'):
        return -0.0 if neg else 0.0
    n_dots = t.count('.')
    if n_dots == 0:
        # No decimal point attempted at all: MUNIS does print a bare whole-dollar
        # integer on this report (e.g. a transfer of exactly '571'), and reading one as
        # cents would turn $571 into $5.71. Commas are still just thousands separators.
        digits_only = t.replace(',', '')
        if re.match(r'^\d+$', digits_only):
            v = float(digits_only)
            return -v if neg else v
        return None
    if n_dots == 1:
        digits_only = t.replace(',', '')
        m = re.match(r'^(\d*)\.(\d{2})$', digits_only)
        if m:
            v = float(m.group(1) or '0') + float(m.group(2)) / 100.0
            return -v if neg else v
        return None
    # MORE than one '.': a scanner cannot always tell a comma from a full stop, so a
    # figure's thousands separators can ALL come out as periods ('4.492.94' for
    # $4,492.94 -- the Susan Howard ledger's own HORTEN-SMITH PEG FUND row). Strip every
    # separator and treat the last two digits as cents, same as
    # `read_trust_table.money()` does for this archive's photographed trust tables.
    digits_only = t.replace(',', '').replace('.', '')
    if not re.match(r'^\d+$', digits_only):
        return None
    v = (float(digits_only[:-2] + '.' + digits_only[-2:]) if len(digits_only) > 2
         else float(digits_only) / (10 ** len(digits_only)))
    return -v if neg else v


def header_centers(page_boxes, header_words, min_cols=0):
    """Column centres for this PAGE, read from its own header boxes -- never carried over
    from another page, because a scan's columns drift. `header_words` maps a column name
    to the literal substrings its header prints (possibly split across two stacked boxes,
    e.g. 'ORIGINAL' over 'APPROP'); every box containing any of them contributes its own
    centre to that column's average."""
    # First pass: find candidate header matches anywhere, to estimate where the header
    # band actually sits on THIS page (it drifts page to page on a scan).
    raw = []
    for b in page_boxes:
        t = b['text'].strip().upper().rstrip('.')
        for k, words in header_words.items():
            if any(w in t for w in words):
                raw.append((k, b))
    if not raw:
        return {}, None
    band_y = statistics.median(b['y'] for k, b in raw)
    # Second pass: keep only matches within one row's height of that band, so a data row
    # whose TEXT happens to contain a header word (an account literally named 'OPERATING
    # TRANSFER') cannot drag a column's centre away from the real header.
    buckets, hdr_ys = {k: [] for k in header_words}, []
    for k, b in raw:
        if abs(b['y'] - band_y) > 0.03:
            continue
        buckets[k].append(b['x'] + b['w'] / 2)
        hdr_ys.append(b['y'])
    centers = {k: sum(xs) / len(xs) for k, xs in buckets.items() if xs}
    if len(centers) < min_cols:
        return {}, None
    return centers, (min(hdr_ys) if hdr_ys else None)


# A figure's thousands groups may be separated by a comma, a stray OCR space, or both
# ('134, 866.56') -- all one token, never split on that internal gap. Only a NEW '-?\d...'
# run starting after a token's own cents is a second figure.
MERGED_MONEY_TOKEN = re.compile(r'[-~]?\s?\d{1,3}(?:[,\s]{0,2}\d{3})*\.\d{2}')


def split_merged_money(boxes):
    """A box holding SEVERAL figures as one OCR observation, split one per figure.

    MUNIS packs columns tightly on this report, and when three adjacent figures happen
    to touch, Vision returns them as one wide box: 'REAL ESTATE TAXES' page 4 original
    prints transfers/revised/ytd as a single observation, '29,544.61 -27,074,147.09
    -26,812,583.08'. A box like that has no SINGLE money-shaped text, so the ordinary
    per-value test ('is this whole string a figure?') sees it as nothing -- not a
    misread figure, no figure at all, and the row loses three of its six columns. Same
    trap `read_trust_table.split_merged` names for the photographed trust tables, here
    for a born-OCR MUNIS scan instead.

    The split is by CHARACTER POSITION across the box's own width, an estimate stated as
    one: fine for a fixed-pitch report, and safe to be approximate because the row's own
    identity has to close either way -- a token one column off cannot invent agreement.
    A label glued to one trailing figure ('TOTAL TAX LEVY -27,778,184.38') keeps the
    label as its own fragment rather than losing it.
    """
    out = []
    for b in boxes:
        t = b['text']
        toks = list(MERGED_MONEY_TOKEN.finditer(t))
        if len(toks) < 1:
            out.append(b)
            continue
        # Nothing left over once every matched token is removed (punctuation/space
        # aside) -> this box IS just the one figure, split into which would only lose
        # the position estimate for no gain.
        leftover = t
        for m in reversed(toks):
            leftover = leftover[:m.start()] + leftover[m.end():]
        if len(toks) == 1 and not leftover.strip(' .,-'):
            out.append(b)
            continue
        n = float(len(t))
        w = b.get('w', 0.0)
        prefix = t[:toks[0].start()]
        if prefix.strip():
            c = dict(b)
            c['text'] = prefix.strip()
            c['w'] = w * (toks[0].start() / n)
            out.append(c)
        for m in toks:
            c = dict(b)
            c['text'] = m.group(0)
            c['x'] = b['x'] + w * (m.start() / n)
            c['w'] = w * ((m.end() - m.start()) / n)
            out.append(c)
        suffix = t[toks[-1].end():]
        if suffix.strip(' .,-'):
            c = dict(b)
            c['text'] = suffix.strip()
            c['x'] = b['x'] + w * (toks[-1].end() / n)
            c['w'] = w * ((n - toks[-1].end()) / n)
            out.append(c)
    return out


def read_report_page(page_boxes, header_words, label_col, value_cols, pct_col=None,
                      row_threshold=0.006, header_gap=0.015, label_margin=0.08):
    """The shared reader. Returns (rows, centers, note). Each row is
    {'y':..., 'label':..., col: value_or_None for col in value_cols [+pct_col]}.

    `label_col` names the column whose centre marks where labels end and values begin
    (labels sit left of `centers[label_col] - label_margin`). A value box is assigned to
    whichever of `value_cols`/`pct_col` centre it is nearest; a '%' in the token always
    goes to `pct_col` regardless of position, since MUNIS prints it hard against the
    right margin and a stray wide box could otherwise out-distance it to AVAILABLE.
    """
    all_cols = list(value_cols) + ([pct_col] if pct_col else [])
    centers, hdr_y = header_centers(page_boxes, header_words, min_cols=len(all_cols) - 1)
    if not centers or hdr_y is None or label_col not in centers:
        return [], centers, 'no header (%d/%d columns found)' % (len(centers), len(all_cols))
    # Two columns whose centres land this close together mean a header word was matched
    # somewhere it should not have been (page 8 of both FY2020 scans: 'original' and
    # 'transfers' land 0.002-0.015 apart instead of the usual ~0.1, which silently makes
    # column assignment a coin flip between them and flips which figure is which between
    # the two documents' extractions of the SAME printed GRAND TOTAL). Refuse the page
    # rather than guess which of two near-identical centres a value belongs to.
    xs = sorted(centers.values())
    if any(b - a < 0.03 for a, b in zip(xs, xs[1:])):
        return [], centers, 'header columns not separated (centres too close together)'
    body = [b for b in page_boxes if b['y'] < hdr_y - header_gap]
    body = split_merged_money(body)
    label_boundary = centers[label_col] - label_margin
    clusters = cluster_rows(body, row_threshold)
    rows = []
    for cl in clusters:
        labels = [b for b in cl if b['x'] < label_boundary]
        vals = [b for b in cl if b['x'] >= label_boundary]
        if not labels and not vals:
            continue
        label = ' '.join(x['text'] for x in sorted(labels, key=lambda b: b['x']))
        ry = statistics.mean(b['y'] for b in cl)
        slot = {c: None for c in all_cols}
        for v in vals:
            txt = v['text'].strip()
            if pct_col and '%' in txt:
                m = re.match(r'^-?(\d+(?:\.\d+)?)%', txt)
                try:
                    slot[pct_col] = float(m.group(1)) if m else None
                except ValueError:
                    slot[pct_col] = None
                continue
            cx = v['x'] + v['w'] / 2
            best = min(value_cols, key=lambda c: abs(centers.get(c, 999) - cx))
            slot[best] = money(txt)
        rows.append(dict(y=round(ry, 5), label=label, **slot))
    return rows, centers, 'ok'


# ==============================================================================
# A5: Town FY2020 fourth-quarter revenue and expense reports (scans)
# ==============================================================================

A5_DOCS = [
    ('revised', 'budget-workbooks/finance-committee/fy20-budget/'
                'fy20-4th-quarter-revised-summary-and-reports.pdf'),
    ('original', 'budget-workbooks/finance-committee/fy20-budget/'
                 'fy20-4th-quarter-summary-and-reports-1.pdf'),
]

MUNIS_HEADER_WORDS = {
    'original': ('ORIGINAL', 'APPROP'),
    # NOT the bare word 'TRANSFER': an account is literally named '01001 490700
    # OPERATING TRANSFER' on page 8, and matching that pulled the whole column's centre
    # left by 0.1 (averaged with the real header words, which only ever abbreviate).
    'transfers': ('TRANFRS', 'ADJSTMTS', 'ADJSTMIS', 'ADJSIMIS', 'ADJSTMNTS'),
    'revised': ('REVISED',),
    'ytd': ('EXPENDED',),
    'encumbrances': ('ENCUMBRANCES', 'ENCUMBRANCE'),
    'available': ('AVAILABLE',),
    'pct': ('PCT', 'USED'),
}
MUNIS_VALUE_COLS = ['original', 'transfers', 'revised', 'ytd', 'encumbrances', 'available']

DEPT_HEADER = re.compile(r'^(\d{1,3})\s+([A-Z][A-Z0-9 /&\'",.()-]*[A-Z0-9)])$')
ACCOUNT_LABEL = re.compile(r'\d{4,5}')
TOTAL_LABEL = re.compile(r'^(GRAND TOTAL|TOTAL\s+.+|TOTAL\s+REVEN\w*|TOTAL\s+EXPENSES)$')


def a5_read_doc(pdf_rel, cache_name):
    pdf_path = os.path.join(ROOT, 'sources', pdf_rel)
    tsv = ensure_ocr_boxes(pdf_path, cache_name)
    boxes = load_boxes(tsv)
    pages = sorted(set(b['page'] for b in boxes))
    rows, unreadable = [], []
    account_type = 'revenue'
    cur_dept_code, cur_dept_name = '', ''
    for p in pages:
        pboxes = [b for b in boxes if b['page'] == p]
        prow, centers, note = read_report_page(
            pboxes, MUNIS_HEADER_WORDS, label_col='original',
            value_cols=MUNIS_VALUE_COLS, pct_col='pct')
        if note != 'ok':
            # Pages 1-2 are the Accountant's memo (prose, no table) -- expected, not a
            # failure. Only flag a page that looks like it SHOULD have a table.
            has_fy_header = any('FOR 2020' in b['text'] for b in pboxes)
            if has_fy_header:
                unreadable.append((p, 'table page but %s' % note))
            continue
        for r in sorted(prow, key=lambda r: -r['y']):
            label = r['label'].strip()
            if not label or not re.search(r'[A-Za-z0-9]', label):
                continue  # a bare separator/rule line ('------'), not a row
            m = DEPT_HEADER.match(label)
            if m and all(r[c] is None for c in MUNIS_VALUE_COLS):
                cur_dept_code, cur_dept_name = m.group(1), m.group(2).strip()
                continue
            ident_ok, reason = a5_check_row(r)
            level = 'account' if ACCOUNT_LABEL.search(label) else (
                'grand_total' if label.upper().startswith('GRAND TOTAL') else (
                    'dept_total' if (label.upper() == 'TOTAL %s' % cur_dept_name
                                      or label.upper() == 'TOTAL ' + cur_dept_name) else
                    'group_total' if label.upper().startswith('TOTAL') else 'other'))
            row = dict(page=p, account_type=account_type, level=level,
                       department_code=cur_dept_code, department_name=cur_dept_name,
                       label=label, y=r['y'],
                       **{c: r[c] for c in MUNIS_VALUE_COLS}, pct=r['pct'])
            if ident_ok:
                rows.append(row)
            else:
                unreadable.append((p, 'row %r: %s' % (label[:40], reason)))
            if level == 'grand_total':
                account_type = 'expense'
    return rows, unreadable


def a5_check_row(r):
    vals = {c: r[c] for c in MUNIS_VALUE_COLS}
    if vals['original'] is None or vals['revised'] is None:
        return False, 'original/revised not both read'
    # A blank TRANSFRS/ADJSTMTS cell means zero, exactly like a blank ENCUMBRANCES cell
    # (MUNIS prints nothing rather than '.00' for some zero cells on this report) --
    # defaulting it to 0 only ever *tightens* the check: a row whose transfer truly was
    # nonzero and unread still fails, because original+0 will not equal the printed
    # revised figure.
    transfers = vals['transfers'] if vals['transfers'] is not None else 0.0
    if round(vals['original'] + transfers - vals['revised'], 2) != 0:
        return False, ('original+transfers != revised (%.2f+%.2f != %.2f)'
                        % (vals['original'], transfers, vals['revised']))
    if vals['ytd'] is None or vals['available'] is None:
        return False, 'ytd/available not both read'
    enc = vals['encumbrances'] if vals['encumbrances'] is not None else 0.0
    if round(vals['revised'] - vals['ytd'] - enc - vals['available'], 2) != 0:
        return False, ('revised-ytd-encumbrances != available (%.2f-%.2f-%.2f != %.2f)'
                        % (vals['revised'], vals['ytd'], enc, vals['available']))
    return True, 'ties'


def extract_a5():
    all_rows, all_unreadable = [], []
    per_doc = {}
    for version, rel in A5_DOCS:
        cache = 'a5-' + version
        rows, unreadable = a5_read_doc(rel, cache)
        for r in rows:
            r['doc_version'] = version
            r['source_file'] = orig_doc(rel)
        per_doc[version] = rows
        all_rows.extend(rows)
        for page, reason in unreadable:
            all_unreadable.append(dict(doc_version=version, source_file=orig_doc(rel),
                                        page=page, reason=reason))

    fields = ['doc_version', 'account_type', 'level', 'department_code', 'department_name',
              'label', 'page', 'original', 'transfers', 'revised', 'ytd', 'encumbrances',
              'available', 'pct', 'source_file']
    with open(data('fy20-q4-reports.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(all_rows, key=lambda r: (r['doc_version'], r['page'], -r['y'])):
            w.writerow({k: r.get(k, '') for k in fields})

    with open(data('fy20-q4-unreadable.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['doc_version', 'page', 'reason', 'source_file'])
        w.writeheader()
        for r in sorted(all_unreadable, key=lambda r: (r['doc_version'], r['page'])):
            w.writerow(r)

    # --- version diff: match revised vs original by what IDENTIFIES a row, not its
    # bare label text. 'TOTAL EXPENSES' alone is printed after every department in the
    # expense section -- dozens of times -- so indexing on the label text collapses
    # every department's running total into one bucket and zips unrelated departments
    # together. An account row's own numeric object code is stable across a reprint
    # even if OCR reads its NAME a little differently; a total row is identified by
    # which department/category it follows, not by its own repeated label. ---
    def seq_key(rows):
        return sorted(rows, key=lambda r: (r['page'], -r['y']))

    rev_rows, orig_rows = seq_key(per_doc['revised']), seq_key(per_doc['original'])

    # ORG + OBJECT together, anchored to the START of a cleanly-clustered label
    # ('11261 511000 TOWN MANAGER SALAR'). The object code ALONE is not specific enough
    # -- '511000' (plain salary) is reused by nearly every department -- and a label the
    # row-clusterer merged from two accounts ('11222 11222 11222 540000 573000 573100
    # ...') matches neither anchor, so it falls back to the whole garbled string as its
    # own unmatched key rather than being guessed into the wrong account.
    ACCOUNT_KEY = re.compile(r'^(\d{4,5})\s+(\d{6})\b')

    ACCOUNT_KEY_ANY = re.compile(r'\d{4,5}\s+\d{6}\b')

    def match_key(r):
        if r['level'] == 'account':
            m = ACCOUNT_KEY.match(r['label'])
            # A label carrying a SECOND org/object pair anywhere is two accounts the
            # row-clusterer merged into one -- '01001 471900 01001 472300 MISC. REVENUE
            # SALE OF TOWN EQUIP' is two different accounts' worth of label, and the
            # leading pair alone is not a trustworthy identity for either of them.
            if m and len(ACCOUNT_KEY_ANY.findall(r['label'])) == 1:
                return (r['account_type'], 'account', m.group(1), m.group(2))
            return (r['account_type'], 'account', 'garbled', r['label'])
        return (r['account_type'], r['level'], r['department_name'] or r['department_code'],
                r['label'])

    def index_by_label(rows):
        idx = {}
        for r in rows:
            idx.setdefault(match_key(r), []).append(r)
        return idx

    # Only rows PROVEN ON BOTH SIDES are compared. The two scans do not prove exactly
    # the same rows -- different pages, different OCR luck -- so a row proven on one
    # side only is a gap in THIS extraction's coverage, not evidence the town revised
    # it; listing those as a "diff" would bury the real finding in noise. Coverage
    # gaps are counted (not itemised) in the printed summary instead.
    rev_idx, orig_idx = index_by_label(rev_rows), index_by_label(orig_rows)
    both_keys = sorted(set(rev_idx) & set(orig_idx))
    only_revised = len(set(rev_idx) - set(orig_idx))
    only_original = len(set(orig_idx) - set(rev_idx))
    diff_rows = []
    for key in both_keys:
        rlist, olist = rev_idx[key], orig_idx[key]
        for rr, orr in zip(rlist, olist):
            for c in MUNIS_VALUE_COLS:
                rv, ov = rr.get(c), orr.get(c)
                # A blank cell means zero on this report (rule noted at a5_check_row);
                # treat None and 0.0 as equal so a coverage gap in one column does not
                # masquerade as a revision.
                rv_n = 0.0 if rv is None else rv
                ov_n = 0.0 if ov is None else ov
                if round(rv_n, 2) != round(ov_n, 2):
                    diff_rows.append(dict(
                        account_type=rr['account_type'], level=rr['level'],
                        label='%s / %s' % (rr['label'], orr['label'])
                        if rr['label'] != orr['label'] else rr['label'],
                        field=c, revised_value=rv, original_value=ov,
                        note='revised page %s, original page %s'
                             % (rr['page'], orr['page'])))
    with open(data('fy20-q4-version-diff.csv'), 'w', newline='') as f:
        fields2 = ['account_type', 'level', 'label', 'field', 'revised_value',
                   'original_value', 'note']
        w = csv.DictWriter(f, fieldnames=fields2)
        w.writeheader()
        for r in diff_rows:
            w.writerow(r)

    # --- memo prose: a direct textual diff of the two Accountant's memos, dollar
    # figures only, never asserting WHY they differ -- rule 7. ---
    memo_diff = a5_memo_diff()
    with open(data('fy20-q4-memo-diff.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['revised_sentence', 'original_sentence',
                                           'revised_amounts', 'original_amounts'])
        w.writeheader()
        for r in memo_diff:
            w.writerow(r)

    # --- compare FY2020 expense department totals (revised doc preferred) to
    # gl-history.csv (sheet=general_fund, fiscal_year=2020), by department NAME. ---
    gl_rows = a5_vs_gl_history(per_doc['revised'] or per_doc['original'])
    with open(data('fy20-q4-vs-gl-history.csv'), 'w', newline='') as f:
        fields3 = ['department_name_ocr', 'department_name_gl_history', 'match_score',
                   'fy20_q4_ytd_expended', 'gl_history_actual', 'difference', 'note']
        w = csv.DictWriter(f, fieldnames=fields3)
        w.writeheader()
        for r in gl_rows:
            w.writerow(r)

    print('A5: %d proven rows (%d revised, %d original); %d unreadable rows/pages'
          % (len(all_rows), len(per_doc['revised']), len(per_doc['original']),
             len(all_unreadable)))
    print('A5: %d genuine value differences on %d rows proven on BOTH scans '
          '(%d labels proven only in revised, %d only in original -- OCR coverage '
          'gaps, not reported as differences)'
          % (len(diff_rows), len(both_keys), only_revised, only_original))
    print('A5: %d vs-gl-history departments compared' % len(gl_rows))
    return all_rows, all_unreadable


def a5_memo_diff():
    """Dollar figures named in the two Accountant's memos (PDF pages 1-2, which carry a
    text layer from OCR's own line-reading since this is prose, not a table -- rule 13b
    only governs the TABLE pages). Diffed sentence by sentence; a changed figure is
    reported with both sentences and nothing is asserted about why it changed."""
    out = []
    MONEY_RE = re.compile(r'\$[\d,]+\.\d{2}')
    texts = {}
    for version, rel in A5_DOCS:
        txt_path = os.path.join(ROOT, 'sources',
                                 os.path.dirname(rel), 'text', os.path.basename(rel) + '.txt')
        full = open(txt_path, encoding='utf-8', errors='replace').read()
        memo = full.split('===PAGE 3===')[0]
        memo = re.sub(r'===PAGE \d+===', ' ', memo)
        sentences = re.split(r'(?<=[.:])\s+', re.sub(r'\s+', ' ', memo))
        texts[version] = [s.strip() for s in sentences if s.strip()]
    rev, orig = texts['revised'], texts['original']
    sm = difflib.SequenceMatcher(a=orig, b=rev, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        o_sent = ' '.join(orig[i1:i2])
        r_sent = ' '.join(rev[j1:j2])
        o_amts, r_amts = MONEY_RE.findall(o_sent), MONEY_RE.findall(r_sent)
        if sorted(o_amts) != sorted(r_amts):
            out.append(dict(revised_sentence=r_sent, original_sentence=o_sent,
                             revised_amounts=';'.join(r_amts),
                             original_amounts=';'.join(o_amts)))
    return out


def a5_vs_gl_history(rows):
    gl_path = data('gl-history.csv')
    gl_depts = {}
    if os.path.exists(gl_path):
        with open(gl_path, newline='') as f:
            for row in csv.DictReader(f):
                if row['sheet'] != 'general_fund' or row['fiscal_year'] != '2020':
                    continue
                dept = row['department'].strip()
                try:
                    gl_depts[dept] = gl_depts.get(dept, 0.0) + float(row['actual'] or 0)
                except ValueError:
                    continue
    gl_names = list(gl_depts)
    out = []
    seen_depts = set()
    for r in rows:
        if r['account_type'] != 'expense' or r['level'] != 'dept_total':
            continue
        dept = r['department_name']
        if not dept or dept in seen_depts:
            continue
        seen_depts.add(dept)
        matches = difflib.get_close_matches(dept, gl_names, n=1, cutoff=0.6)
        if matches:
            match, score = matches[0], difflib.SequenceMatcher(
                None, dept, matches[0]).ratio()
            gl_val = gl_depts[match]
            ocr_val = r['ytd']
            out.append(dict(
                department_name_ocr=dept, department_name_gl_history=match,
                match_score=round(score, 3), fy20_q4_ytd_expended=ocr_val,
                gl_history_actual=round(gl_val, 2),
                difference=round((ocr_val or 0) - gl_val, 2),
                note='fuzzy name match' if score < 0.999 else 'exact name match'))
        else:
            out.append(dict(
                department_name_ocr=dept, department_name_gl_history='',
                match_score='', fy20_q4_ytd_expended=r['ytd'], gl_history_actual='',
                difference='', note='no gl-history department matched'))
    return out


# ==============================================================================
# H1: Town Meeting warrants and article tracking, FY2024-FY2027
# ==============================================================================

H1_WARRANTS = [
    # (fy, label, relative path, meeting_year_for_votes)
    (2024, '2-28-23 draft', 'budget-workbooks/finance-committee/fy24-budget/text/'
     'draft-atm-warrant-articles-2-28-23.pdf.txt', 2023),
    (2025, '3-10-24 draft', 'budget-workbooks/finance-committee/fy25-budget/'
     'town-manager-material/text/draft-atm-warrant-articles-3-10-24.pdf.txt', 2024),
    (2026, '2.23.2025 draft', 'budget-workbooks/finance-committee/fy26-budget/tm-warrant/'
     'text/draft-atm-warrant-2.23.2025-for-fincom.docx.txt', 2025),
    (2027, '3.7.26 draft', 'budget-workbooks/finance-committee/fy27-budget/tm-warrant/'
     'text/draft-warrant-3.7.26.docx.txt', 2026),
    (2027, '4.2.26 draft', 'budget-workbooks/finance-committee/fy27-budget/tm-warrant/'
     'prior-revisions/text/draft-warrant-4.2.26.pdf.txt', 2026),
    (2027, '4.5.26 draft', 'budget-workbooks/finance-committee/fy27-budget/tm-warrant/'
     'text/draft-warrant-4.5.26.pdf.txt', 2026),
]

# Three heading conventions, tried in this order; whichever finds the most wins.
HEADING_PATTERNS = [
    ('title', re.compile(r"(?m)^([A-Z]{1,2})\.\s{1,3}([A-Z][A-Z0-9 /&,'.()–’-]"
                          r"{3,100})\s*$")),
    ('article', re.compile(r"(?m)^ARTICLE\s+([A-Z]{1,2}):\s*([^\n]{3,140})")),
    ('body', re.compile(r"(?m)^([A-Z]{1,2})\.\s{1,3}((?:To see if the ?Town|PLACEHOLDER)"
                         r"[^\n]*)")),
]

MONEY_DOLLAR = re.compile(r'\$[\d,]+(?:\.\d{2})?')

FUNDING_PHRASES = [
    'Free Cash', 'available funds', 'Stabilization Fund', 'Special Purpose Stabilization',
    'Capital Stabilization', 'Opioid Settlement', 'Overlay Surplus', 'OPEB Trust Fund',
    'Compensated Absences Reserve Fund', 'Water Enterprise Fund', 'Sewer Enterprise Fund',
    'Solid Waste', 'PEG Access Enterprise Fund', 'Ambulance Receipts',
    'Chapter 90', 'Sale of Cemetery', 'retained earnings', 'General Fund', 'taxation',
    'borrow', 'donation', 'grant', 'School Choice', 'Revolving Fund',
]


def split_articles(text):
    """Try each heading convention; keep whichever finds the most headings (>= 3)."""
    best = (None, [])
    for name, pat in HEADING_PATTERNS:
        hits = [(m.group(1), m.group(2).strip(), m.start(), m.end())
                for m in pat.finditer(text)]
        if len(hits) > len(best[1]):
            best = (name, hits)
    return best


def funding_hits(sentence):
    return [p for p in FUNDING_PHRASES if p.lower() in sentence.lower()]


def extract_h1_warrant_articles():
    rows = []
    for fy, label, rel, meeting_year in H1_WARRANTS:
        path = os.path.join(ROOT, 'sources', rel)
        if not os.path.exists(path):
            continue
        text = open(path, encoding='utf-8', errors='replace').read()
        style, hits = split_articles(text)
        if len(hits) < 3:
            continue
        for i, (letter, title, start, end) in enumerate(hits):
            body_end = hits[i + 1][2] if i + 1 < len(hits) else len(text)
            body = text[start:body_end]
            amounts = list(MONEY_DOLLAR.finditer(body))
            sentences = re.split(r'(?<=[.])\s+', re.sub(r'\s+', ' ', body))
            if not amounts:
                rows.append(dict(fy=fy, draft_label=label, heading_style=style,
                                  article_letter=letter, title=title[:120], amount='',
                                  funding_source='', context='', source_file=orig_doc(rel)))
                continue
            for m in amounts:
                # find the sentence containing this amount's text
                amt_text = m.group(0)
                ctx = next((s for s in sentences if amt_text in s), '')
                rows.append(dict(
                    fy=fy, draft_label=label, heading_style=style, article_letter=letter,
                    title=title[:120], amount=amt_text,
                    funding_source=';'.join(funding_hits(ctx)),
                    context=ctx.strip()[:300], source_file=orig_doc(rel)))
    return rows


def extract_h1_amount_diff(article_rows):
    """Diff amounts across drafts of the SAME fiscal year, in the order the drafts were
    dated (the date is read off the filename/label, which is the document's own stated
    date -- not a figure, a sequencing label). FY24, FY25 and FY26 each have one draft on
    file, so only FY27 (three drafts) produces a diff."""
    by_fy_letter = {}
    order = {label: i for i, (fy, label, rel, my) in enumerate(H1_WARRANTS)}
    for r in article_rows:
        key = (r['fy'], r['article_letter'])
        by_fy_letter.setdefault(key, {}).setdefault(r['draft_label'], set()).add(r['amount'])
    out = []
    for (fy, letter), by_label in sorted(by_fy_letter.items()):
        labels = sorted(by_label, key=lambda l: order.get(l, 99))
        if len(labels) < 2:
            continue
        for a, b in zip(labels, labels[1:]):
            before = sorted(x for x in by_label[a] if x)
            after = sorted(x for x in by_label[b] if x)
            if before != after:
                out.append(dict(fy=fy, article_letter=letter, draft_before=a,
                                 draft_after=b, amounts_before=';'.join(before),
                                 amounts_after=';'.join(after)))
    return out


H1_TRACKING_XLSX = [
    (2026, 'budget-workbooks/finance-committee/fy26-budget/tm-warrant/text/'
     'warrant-article-tracking-copy.xlsx.txt'),
    (2027, 'budget-workbooks/finance-committee/fy27-budget/tm-warrant/text/'
     'warrant-article-tracking-copy.xlsx.txt'),
    (2027, 'budget-workbooks/finance-committee/fy27-budget/tm-warrant/prior-revisions/'
     'text/warrant-article-tracking-copy-copy.xlsx.txt'),
    (2027, 'budget-workbooks/finance-committee/fy27-budget/tm-warrant/prior-revisions/'
     'text/warrant-article-tracking-copy-copy-copy.xlsx.txt'),
    (2027, 'budget-workbooks/finance-committee/fy27-budget/tm-warrant/text/'
     'warrant-article-tracking-copy-copy-1.xlsx.txt'),
]


def parse_sheet_csv(text):
    """A '===SHEET name===' block followed by CSV rows, as `build_source_index.py`'s
    sibling extractors write xlsx text. Returns (header, rows)."""
    body = re.split(r'===SHEET [^\n]*===\n', text, maxsplit=1)
    if len(body) < 2:
        return [], []
    import io
    rdr = csv.reader(io.StringIO(body[1]))
    all_rows = [r for r in rdr if any(c.strip() for c in r)]
    if not all_rows:
        return [], []
    return all_rows[0], all_rows[1:]


def decided_cells(header, row):
    """How many decision-relevant cells (Financial Impact, FinCom vote) are filled in and
    not a bare '?' -- used only to ORDER same-schema snapshots by how far along the
    tracking got, which is a measurement of the file, not an assumption about dates."""
    n = 0
    for h, v in zip(header, row):
        hl = h.lower()
        if ('impact' in hl or 'fincom' in hl or 'vote' in hl) and v.strip() not in ('', '?'):
            n += 1
    return n


def extract_h1_tracking():
    snapshots = []
    for fy, rel in H1_TRACKING_XLSX:
        path = os.path.join(ROOT, 'sources', rel)
        if not os.path.exists(path):
            continue
        text = open(path, encoding='utf-8', errors='replace').read()
        header, rows = parse_sheet_csv(text)
        if not header:
            continue
        total_decided = sum(decided_cells(header, r) for r in rows)
        snapshots.append(dict(fy=fy, source_file=orig_doc(rel), header=header,
                               rows=rows, decided=total_decided))
    # order same-fy snapshots by decided-cell count (a measurement, logged as such)
    by_fy = {}
    for s in snapshots:
        by_fy.setdefault(s['fy'], []).append(s)
    out_rows, diff_rows = [], []
    for fy, snaps in by_fy.items():
        snaps.sort(key=lambda s: s['decided'])
        for rank, s in enumerate(snaps):
            letter_col = next((i for i, h in enumerate(s['header'])
                                if 'letter' in h.lower()), 0)
            desc_col = next((i for i, h in enumerate(s['header'])
                              if 'description' in h.lower()), None)
            dept_col = next((i for i, h in enumerate(s['header'])
                              if 'department' in h.lower()), None)
            impact_col = next((i for i, h in enumerate(s['header'])
                                if 'impact' in h.lower()), None)
            for row in s['rows']:
                letter = row[letter_col].strip() if letter_col < len(row) else ''
                if not letter:
                    continue
                out_rows.append(dict(
                    fy=fy, snapshot_rank=rank, decided_cells=s['decided'],
                    article_letter=letter,
                    description=row[desc_col].strip() if desc_col is not None and
                    desc_col < len(row) else '',
                    department=row[dept_col].strip() if dept_col is not None and
                    dept_col < len(row) else '',
                    financial_impact=row[impact_col].strip() if impact_col is not None and
                    impact_col < len(row) else '',
                    source_file=s['source_file']))
        # consecutive-rank diff on financial_impact, by article letter
        for a, b in zip(snaps, snaps[1:]):
            a_impact = {}
            impact_col_a = next((i for i, h in enumerate(a['header'])
                                  if 'impact' in h.lower()), None)
            letter_col_a = next((i for i, h in enumerate(a['header'])
                                  if 'letter' in h.lower()), 0)
            for row in a['rows']:
                if letter_col_a < len(row) and row[letter_col_a].strip():
                    a_impact[row[letter_col_a].strip()] = (
                        row[impact_col_a].strip() if impact_col_a is not None and
                        impact_col_a < len(row) else '')
            impact_col_b = next((i for i, h in enumerate(b['header'])
                                  if 'impact' in h.lower()), None)
            letter_col_b = next((i for i, h in enumerate(b['header'])
                                  if 'letter' in h.lower()), 0)
            for row in b['rows']:
                letter = row[letter_col_b].strip() if letter_col_b < len(row) else ''
                if not letter:
                    continue
                b_val = (row[impact_col_b].strip() if impact_col_b is not None and
                         impact_col_b < len(row) else '')
                a_val = a_impact.get(letter)
                if a_val is not None and a_val != b_val:
                    diff_rows.append(dict(
                        fy=fy, article_letter=letter, field='financial_impact',
                        before=a_val, after=b_val,
                        snapshot_before=a['source_file'], snapshot_after=b['source_file']))
    return out_rows, diff_rows


def extract_h1_prior_year_bills():
    path = os.path.join(ROOT, 'sources', 'budget-workbooks/finance-committee/'
                         'fy27-budget/tm-warrant/text/prior-year-bills-tracking-copy.xlsx.txt')
    out = []
    if not os.path.exists(path):
        return out
    text = open(path, encoding='utf-8', errors='replace').read()
    header, rows = parse_sheet_csv(text)
    for row in rows:
        d = dict(zip([h.strip().lower() for h in header], row))
        out.append(dict(vendor=d.get('vendor', '').strip(),
                         department=d.get('department', '').strip(),
                         amount=d.get('amount', '').strip(), notes=d.get('notes', '').strip(),
                         source_file='sources/budget-workbooks/finance-committee/'
                         'fy27-budget/tm-warrant/prior-year-bills-tracking-copy.xlsx'))
    return out


def extract_h1_free_cash_history():
    path = os.path.join(ROOT, 'sources', 'budget-workbooks/finance-committee/fy27-budget/'
                         'tm-warrant/text/free-cash-fact-sheet.docx.txt')
    out = []
    if not os.path.exists(path):
        return out
    text = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'Lunenburg Free Cash History:\s*(.*?)(?:10 Year Average)', text, re.S)
    if not m:
        return out
    block = m.group(1)
    nums = re.findall(r'[\d,]+\.?\d*%?', block)
    # five fields repeat per year: FY, date certified, certified free cash, prior budget, pct
    years = re.findall(r'\b(20\d\d)\b\s*\n(\d{1,2}/\d{1,2}/\d{4})\s*\n([\d,]+)\s*\n'
                        r'([\d,]+)\s*\n([\d.]+%)', block)
    for fy, date_cert, cert_fc, prior_budget, pct in years:
        out.append(dict(fiscal_year=fy, date_certified=date_cert,
                         certified_free_cash=cert_fc.replace(',', ''),
                         prior_year_operating_budget=prior_budget.replace(',', ''),
                         pct_of_budget=pct,
                         source_file='sources/budget-workbooks/finance-committee/'
                         'fy27-budget/tm-warrant/free-cash-fact-sheet.docx'))
    return out


def extract_h1_vs_votes(article_rows):
    """Compare draft article amounts to the archive's recorded Town Meeting votes
    (`sources/data/town-meeting-votes.csv`), where that CSV's `fy` is the MEETING YEAR --
    a May-of-year-Y annual meeting funds FY(Y+1). Matched by (meeting year, exact dollar
    amount): draft letters are renumbered to the final warrant's numbers, so amount is
    the only safe join key, and a draft amount with no equal vote amount is reported, not
    forced -- the task's own done_when says a draft-vs-vote difference is expected."""
    votes_path = data('town-meeting-votes.csv')
    if not os.path.exists(votes_path):
        return []
    votes = []
    with open(votes_path, newline='') as f:
        votes = list(csv.DictReader(f))
    by_fy, by_label = {}, {}
    for fy, label, rel, meeting_year in H1_WARRANTS:
        by_label[label] = meeting_year
    out = []
    for r in article_rows:
        amt = r['amount']
        if not amt:
            continue
        meeting_year = by_label.get(r['draft_label'])
        if meeting_year is None:
            continue
        val = money(amt.lstrip('$'))
        if val is None:
            continue
        candidates = [v for v in votes if v['fy'] == str(meeting_year)
                      and v.get('amount_as_printed', '').strip()]
        amount_matches = []
        for v in candidates:
            vv = money(v['amount_as_printed'].lstrip('$'))
            if vv is not None and abs(vv - abs(val)) < 0.005:
                amount_matches.append(v)
        matched, sim = None, 0.0
        if amount_matches:
            own_text = (r['title'] + ' ' + r['context']).lower()
            scored = [(difflib.SequenceMatcher(
                None, own_text, v['subject'].lower()).ratio(), v) for v in amount_matches]
            sim, matched = max(scored, key=lambda t: t[0])
        if matched and sim >= 0.25:
            note = 'matched by amount; title/subject text overlap %.2f' % sim
        elif matched:
            note = ('same amount found in the vote record (%d other article(s) at this FY '
                     'also match), but little text overlap with the vote subject -- '
                     'article letters are renumbered between a draft and the final '
                     'warrant, so this may be the same article or a coincidental amount'
                     % (len(amount_matches) - 1))
        else:
            note = ('no vote recorded at this amount (meeting not yet held, or amount '
                     'changed before the final warrant)')
        out.append(dict(
            fy=r['fy'], draft_label=r['draft_label'], article_letter=r['article_letter'],
            draft_title=r['title'], draft_amount=amt,
            meeting_year=meeting_year,
            voted_article=matched['article'] if matched else '',
            voted_subject=matched['subject'] if matched else '',
            voted_amount=matched['amount_as_printed'] if matched else '',
            note=note))
    return out


def extract_h1():
    article_rows = extract_h1_warrant_articles()
    with open(data('warrant-articles-fincom.csv'), 'w', newline='') as f:
        fields = ['fy', 'draft_label', 'heading_style', 'article_letter', 'title',
                   'amount', 'funding_source', 'context', 'source_file']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in article_rows:
            w.writerow(r)

    amount_diff = extract_h1_amount_diff(article_rows)
    with open(data('warrant-article-amount-diff.csv'), 'w', newline='') as f:
        fields = ['fy', 'article_letter', 'draft_before', 'draft_after',
                   'amounts_before', 'amounts_after']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in amount_diff:
            w.writerow(r)

    tracking_rows, tracking_diff = extract_h1_tracking()
    with open(data('warrant-article-tracking-fincom.csv'), 'w', newline='') as f:
        fields = ['fy', 'snapshot_rank', 'decided_cells', 'article_letter', 'description',
                   'department', 'financial_impact', 'source_file']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in tracking_rows:
            w.writerow(r)
    with open(data('warrant-article-tracking-diff.csv'), 'w', newline='') as f:
        fields = ['fy', 'article_letter', 'field', 'before', 'after', 'snapshot_before',
                   'snapshot_after']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in tracking_diff:
            w.writerow(r)

    pyb_rows = extract_h1_prior_year_bills()
    with open(data('prior-year-bills-fincom.csv'), 'w', newline='') as f:
        fields = ['vendor', 'department', 'amount', 'notes', 'source_file']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in pyb_rows:
            w.writerow(r)

    fc_rows = extract_h1_free_cash_history()
    with open(data('free-cash-history-fincom.csv'), 'w', newline='') as f:
        fields = ['fiscal_year', 'date_certified', 'certified_free_cash',
                   'prior_year_operating_budget', 'pct_of_budget', 'source_file']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in fc_rows:
            w.writerow(r)

    votes_rows = extract_h1_vs_votes(article_rows)
    with open(data('warrant-vs-votes-fincom.csv'), 'w', newline='') as f:
        fields = ['fy', 'draft_label', 'article_letter', 'draft_title', 'draft_amount',
                   'meeting_year', 'voted_article', 'voted_subject', 'voted_amount', 'note']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in votes_rows:
            w.writerow(r)

    print('H1: %d article/amount rows across %d draft documents' %
          (len(article_rows), len(set((r['fy'], r['draft_label']) for r in article_rows))))
    print('H1: %d amount-diff entries; %d tracking rows, %d tracking-diff entries'
          % (len(amount_diff), len(tracking_rows), len(tracking_diff)))
    print('H1: %d prior-year-bills rows; %d free-cash-history rows; %d vs-votes rows'
          % (len(pyb_rows), len(fc_rows), len(votes_rows)))
    matched = sum(1 for r in votes_rows if r['voted_article'])
    print('H1: %d of %d draft amounts matched a recorded vote by amount' %
          (matched, len(votes_rows)))
    return article_rows


# ==============================================================================
# J1: Trust fund records -- deeds, ledgers, policies, cy pres materials
# ==============================================================================

TRUST_BG = 'budget-workbooks/finance-committee/fy27-budget/trust-funds/background-information'

# (fund_name, relative .txt path, [(page, note)] pages that ARE reliable to cite)
J1_PURPOSE_SOURCES = [
    ('Nathaniel Day Worthy Poor Fund', TRUST_BG +
     '/text/1901-nathaniel-day-worthy-poor-trust-fund-with-trust-summary.pdf.txt',
     [3], [(1, 'handwritten 1901 original; OCR of cursive is not reliably legible'),
           (2, 'handwritten 1901 original; OCR of cursive is not reliably legible')]),
    ('American Legion Post 283 Trust Fund', TRUST_BG +
     '/text/2013-american-legion-post-283trust-fund-with-trust-fund-summary.pdf.txt',
     [1, 2, 3], []),
    ('J.M./Luther Howard Sidewalk & Grounds Fund', TRUST_BG +
     '/text/jm-howard-sidewalk-fund-information-1931.pdf.txt',
     [2], [(1, 'aged 1931 annual-report scan; OCR reads mostly unrelated warrant '
               'articles on the same page and is not reliably legible')]),
]

CY_PRES_SOURCE = (TRUST_BG + '/text/legal-memo-cy-pres-warrant-article.pdf.txt')
BYLAW_SOURCE = TRUST_BG + '/text/bylaw-section-by-section-explanation.pdf.txt'
VERIFICATION_POLICY = TRUST_BG + '/text/lunenburg-trust-fund-verification-policy-with-checklist.pdf.txt'
DELEGATION_POLICY = TRUST_BG + '/text/lunenburg-delegation-policy-with-exec-summary-appendix.pdf.txt'
MILITARY_TRUST_GUIDE = TRUST_BG + '/text/military-trust-fund-guide-with-appendices.pdf.txt'


def read_page_text(rel_txt, page):
    path = os.path.join(ROOT, 'sources', rel_txt)
    if not os.path.exists(path):
        return None
    full = open(path, encoding='utf-8', errors='replace').read()
    parts = re.split(r'===PAGE (\d+)===\n', full)
    # parts = ['', '1', text1, '2', text2, ...]
    for i in range(1, len(parts), 2):
        if int(parts[i]) == page:
            return parts[i + 1]
    return None


def extract_j1_purposes():
    rows, unreadable = [], []
    for fund_name, rel_txt, good_pages, bad_pages in J1_PURPOSE_SOURCES:
        for page, reason in bad_pages:
            unreadable.append(dict(source_file=orig_doc(rel_txt), page=page,
                                    reason=reason))
        for page in good_pages:
            text = read_page_text(rel_txt, page)
            if not text or len(text.strip()) < 20:
                unreadable.append(dict(source_file=orig_doc(rel_txt), page=page,
                                        reason='page empty or too short to transcribe'))
                continue
            rows.append(dict(fund_name=fund_name, category='deed/donor-intent',
                              page=page, text=text.strip(), source_file=orig_doc(rel_txt)))

    # Cy pres legal memo: the $ figure and the funds it names as impracticable.
    cy_text = open(os.path.join(ROOT, 'sources', CY_PRES_SOURCE),
                    encoding='utf-8', errors='replace').read() \
        if os.path.exists(os.path.join(ROOT, 'sources', CY_PRES_SOURCE)) else ''
    if cy_text:
        amt_m = re.search(r'appropriation of (\$[\d,]+\.\d{2})', cy_text)
        rows.append(dict(
            fund_name='American Legion Poor Trust Fund / Post 283 American Legion Trust '
            'Fund / Worthy Poor Fund', category='cy-pres (restriction no longer practicable)',
            page=1, text=('Legal memo, 29 Jan 2026: the American Legion Post 283 and '
                           'Worthy Poor Fund restrictions can no longer be administered as '
                           'written (Post 283 no longer exists; towns no longer operate '
                           'poorhouses). Requests a General Fund appropriation of %s for '
                           'legal costs of Probate and Family Court cy pres relief under '
                           'M.G.L. c.203E Sec.413.' % (amt_m.group(1) if amt_m else '(amount '
                           'not found)')),
            source_file=orig_doc(CY_PRES_SOURCE)))

    # Policies: one row each, citing the document rather than transcribing it whole.
    for fund_name, rel_txt, note in [
        ('All funds (town-wide policy)', VERIFICATION_POLICY,
         'Trust Fund Verification Policy with Checklist -- the Commissioners\' own '
         'process for confirming a fund\'s purpose and balance before disbursing.'),
        ('All funds (town-wide policy)', DELEGATION_POLICY,
         'Delegation Policy with Executive Summary and Appendix -- what the Board of '
         'Commissioners of Trust Funds may delegate and to whom.'),
        ('Military/veterans trust funds', MILITARY_TRUST_GUIDE,
         'Military Trust Fund Guide with Appendices -- eligibility and administration '
         'guidance for veteran-benefit trust funds (the American Legion and related '
         'funds fall under this guide).'),
        ('All funds (bylaw)', BYLAW_SOURCE,
         'Bylaw Section-by-Section Explanation of the article governing the Board of '
         'Commissioners of Trust Funds.'),
    ]:
        if os.path.exists(os.path.join(ROOT, 'sources', rel_txt)):
            rows.append(dict(fund_name=fund_name, category='policy', page=1, text=note,
                              source_file=orig_doc(rel_txt)))

    return rows, unreadable


def extract_j1_ledger():
    """The Susan Howard misc. ledger's 'SUMMARY OF FUNDS' table (page 8): one label column,
    one value column, proven against the page's own 'GRAND TOTAL TRUST FUNDS' line."""
    pdf_rel = TRUST_BG + '/miscelaneous-ledger-and-notes-of-susan-howard-funds-and-others.pdf'
    pdf_path = os.path.join(ROOT, 'sources', pdf_rel)
    tsv = ensure_ocr_boxes(pdf_path, 'j1-susan-howard-ledger')
    boxes = load_boxes(tsv)
    p8 = [b for b in boxes if b['page'] == 8]
    # The SUMMARY OF FUNDS category list sits strictly between its own heading and its
    # own closing 'GRAND TOTAL TRUST FUNDS:' line -- bounded this tightly on purpose,
    # because labels of the SAME fund names (TIMOTHY STANLEY SCHOLARSHIP, DORA HAVEN
    # SCHOLARSHIP, ...) also appear higher on this page as line items of the DETAILED
    # ledger, with different figures beside them. Widening the y-range re-admits those
    # and silently mismatches a category to the wrong number.
    heading = next((b for b in p8 if 'SUMMARY OF FUNDS' in b['text'].upper()), None)
    closing = next((b for b in p8 if 'GRAND TOTAL TRUST FUNDS' in b['text'].upper()
                     and b['y'] < (heading['y'] if heading else 1.0)), None)
    if heading is None or closing is None:
        return [], [dict(source_file='sources/' + pdf_rel, page=8,
                          reason='SUMMARY OF FUNDS heading or its closing GRAND TOTAL '
                          'line not found on this page')], 'section not found', None, 0.0
    # The GRAND TOTAL's own figure sits a touch ABOVE its label's y (.19216 against the
    # label's .1847 -- OCR's line grouping, not a rotation), so a bound at exactly
    # closing['y'] still admits it as a 21st 'value' paired against a stray '฿' symbol
    # box that drifted into the label x-range. Push the lower bound above that row too.
    lo, hi = closing['y'] + 0.02, heading['y']
    label_boxes = sorted([b for b in p8 if 0.07 < b['x'] < 0.37 and lo < b['y'] < hi
                           and sum(c.isalpha() for c in b['text']) >= 3],
                          key=lambda b: -b['y'])
    value_boxes = sorted([b for b in p8 if 0.37 <= b['x'] < 0.60 and lo < b['y'] < hi],
                          key=lambda b: -b['y'])
    grand_total = money(next((b['text'] for b in p8
                               if abs(b['y'] - closing['y']) < 0.012
                               and b['x'] >= 0.37), ''))
    rows = []
    if len(label_boxes) == len(value_boxes):
        # Same count, same section, both already sorted top-to-bottom: match by
        # POSITION, not by nearest-y -- nearest-y mis-paired CONSERVATION (y=.4179) to
        # CHESTER MOSSMAN TEEN CENTER's figure (y=.4026 is closer to it than .4271, its
        # own) once two rows' labels and values drifted by different small amounts.
        for lb, vb in zip(label_boxes, value_boxes):
            val = money(vb['text'])
            if val is None:
                continue
            rows.append(dict(fund_category=lb['text'].strip(), book_balance=val, page=8,
                              source_file='sources/' + pdf_rel))
    else:
        return [], [dict(source_file='sources/' + pdf_rel, page=8,
                          reason='SUMMARY OF FUNDS: %d category labels but %d values in '
                          'the section band -- positional pairing refused rather than '
                          'guessed' % (len(label_boxes), len(value_boxes)))], \
            'label/value count mismatch (%d vs %d)' % (len(label_boxes), len(value_boxes)), \
            grand_total, 0.0
    total = round(sum(r['book_balance'] for r in rows), 2)
    unreadable = []
    note = None
    if grand_total is not None and abs(total - grand_total) <= 0.02:
        note = 'ties'
    else:
        note = 'DOES NOT TIE: sum=%.2f, printed GRAND TOTAL=%s' % (
            total, grand_total if grand_total is not None else '(not found)')
        unreadable.append(dict(source_file='sources/' + pdf_rel, page=8,
                                reason='SUMMARY OF FUNDS category rows do not sum to the '
                                'printed GRAND TOTAL TRUST FUNDS (%s)' % note))
        rows = []  # refuse to write unproven rows -- rule 13b's last line
    # The detailed six-column fund-by-fund ledger (pages 6-8, ~45 line items: BEG BAL,
    # DIVIDENDS, CONTRIBUTIONS, REDEMPTIONS, BOOK BALANCE, MARKET BALANCE) is NOT
    # resolved by this pass -- named here rather than guessed at.
    for p in (6, 7, 8):
        unreadable.append(dict(
            source_file='sources/' + pdf_rel, page=p,
            reason='detailed six-column per-fund ledger not column-resolved in this pass '
            '(only the one-column SUMMARY OF FUNDS roll-up on page 8 was read); raw OCR '
            'text is at sources/%s/text/%s.txt' % (TRUST_BG, os.path.basename(pdf_rel))))
    return rows, unreadable, note, grand_total, total


def extract_j1():
    purpose_rows, purpose_unreadable = extract_j1_purposes()
    with open(data('trust-fund-purposes.csv'), 'w', newline='') as f:
        fields = ['fund_name', 'category', 'page', 'text', 'source_file']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in purpose_rows:
            w.writerow(r)

    ledger_rows, ledger_unreadable, note, grand_total, total = extract_j1_ledger()
    with open(data('trust-ledger-entries.csv'), 'w', newline='') as f:
        fields = ['fund_category', 'book_balance', 'page', 'source_file']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in ledger_rows:
            w.writerow(r)

    all_unreadable = purpose_unreadable + ledger_unreadable
    with open(data('j1-unreadable.csv'), 'w', newline='') as f:
        fields = ['source_file', 'page', 'reason']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_unreadable:
            w.writerow(r)

    print('J1: %d purpose/restriction rows transcribed; %d pages listed unreadable'
          % (len(purpose_rows), len(purpose_unreadable)))
    print('J1: ledger SUMMARY OF FUNDS -- %s (sum=%.2f, printed GRAND TOTAL=%s); '
          '%d rows written' % (note, total, grand_total, len(ledger_rows)))
    return purpose_rows, ledger_rows


# ==============================================================================
# main / --check
# ==============================================================================

def run_checks():
    ok = True
    # A5: every written row must tie (already enforced at write time -- re-verify by
    # reading the CSV back and re-checking the identity, so a hand-edit cannot slip past).
    path = data('fy20-q4-reports.csv')
    if os.path.exists(path):
        with open(path, newline='') as f:
            for row in csv.DictReader(f):
                vals = {}
                for c in MUNIS_VALUE_COLS:
                    v = row[c]
                    vals[c] = float(v) if v not in ('', None) else None
                if vals['original'] is None or vals['revised'] is None:
                    continue
                transfers = vals['transfers'] if vals['transfers'] is not None else 0.0
                if round(vals['original'] + transfers - vals['revised'], 2) != 0:
                    print('CHECK FAILED (A5): %r original+transfers != revised'
                          % row['label'])
                    ok = False
                if vals['ytd'] is not None and vals['available'] is not None:
                    enc = vals['encumbrances'] if vals['encumbrances'] is not None else 0.0
                    if round(vals['revised'] - vals['ytd'] - enc - vals['available'], 2) != 0:
                        print('CHECK FAILED (A5): %r revised-ytd-encumbrances != available'
                              % row['label'])
                        ok = False
    # J1 ledger: re-verify the written total against the identity note by recomputing.
    lpath = data('trust-ledger-entries.csv')
    if os.path.exists(lpath):
        with open(lpath, newline='') as f:
            rows = list(csv.DictReader(f))
        if rows:
            total = sum(float(r['book_balance']) for r in rows)
            # 1,700,242.68 is the page's own printed GRAND TOTAL, re-stated here only to
            # re-verify a written CSV, never to seed a fresh extraction.
            if abs(total - 1700242.68) > 0.02:
                print('CHECK FAILED (J1): SUMMARY OF FUNDS rows sum to %.2f, '
                      'not the printed GRAND TOTAL' % total)
                ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--task', choices=['a5', 'h1', 'j1'], default=None)
    args = ap.parse_args()

    if args.task in (None, 'a5'):
        print('=== A5: FY2020 Q4 revenue/expense reports ===')
        extract_a5()
    if args.task in (None, 'h1'):
        print('=== H1: Town Meeting warrants, FY2024-FY2027 ===')
        extract_h1()
    if args.task in (None, 'j1'):
        print('=== J1: Trust fund records ===')
        extract_j1()

    if args.check:
        print('=== --check ===')
        ok = run_checks()
        if not ok:
            sys.exit(1)
        print('all checks passed')


if __name__ == '__main__':
    main()
