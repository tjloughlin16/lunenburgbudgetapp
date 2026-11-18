#!/usr/bin/env python3
"""PRIVATE. A MUNIS `glytdbud` PDF whose text layer is unreadable, rebuilt from Textract's words.

    python3.11 scripts/extract_munis_textract_private.py PDF [PDF...]

The Town's general fund reports at period 13, FY2025 and FY2026 (delivered 17 November 2026,
`PROVENANCE-fy2025-fy2026-p13-gf-all.md`), were printed through a PostScript driver whose fonts
carry no character map: both text extractors return glyph ids on 278 of 278 pages. The pages
render cleanly, so they are read by the project's existing reader, `textract_pages.py`, through
the meter -- this script spends nothing. It reads only the cached responses
(`build/textract/cache/<sha256>/p<NNN>-text.json`) for the PDF it is given.

PRIVATE, like `extract_munis_xlsx_private.py`: CLAUDE.md 13e holds MUNIS at the gate until our
own review writes `publish` in redactions.csv, so everything here goes to gitignored
`build/private/munis/`. Nothing lands in sources/, fy28/ or the database from this script.

HOW A ROW IS BUILT (CLAUDE.md 13b, applied to a digital page that needs no rotation):
  * words are banded into rows by their top edge, the band being half the page's own row pitch;
  * a figure is placed in the column whose RIGHT EDGE it is nearest -- MUNIS right-aligns them --
    never by its order in the row, so a blank column stays blank;
  * the column edges are measured from the figures themselves (the median right edge of each
    cluster), not typed in.

An account is its full account string (`0100-1-122-0000-00-0-00-1-511000`), its description
(printed on the account's row), and the next row of figures -- which may sit on the NEXT page.

WHAT IT CHECKS before writing, against identities the report prints about itself:
  1. every `TOTAL <object>` line equals the sum of the accounts under that object, column by
     column;
  2. the sum of all accounts equals the report's last fund-level total (`TOTAL GENERAL FUND` or
     the GRAND TOTAL, whichever the report prints last), column by column;
  3. AVAILABLE = REVISED - EXPENDED - ENCUMBERED on every account, and REVISED = ORIGINAL +
     TRANSFERS.
A failure is printed with the page and refuses the write; nothing is averaged or forced.
"""
import csv
import glob
import hashlib
import json
import os
import re
import statistics
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'build', 'textract', 'cache')
OUT = os.path.join(ROOT, 'build', 'private', 'munis')

ACCOUNT = re.compile(r'^\d{4}(?:-\d+){8}$')
MONEY = re.compile(r'^-?[\d,]*\.\d{2}-?$')
PCT = re.compile(r'^-?[\d,]*\.\d%$')
COLS = ['original', 'transfers', 'revised', 'expended', 'encumbered', 'available']
HEADER_WORDS = {'ORIGINAL', 'APPROP', 'TRANFRS/', 'ADJSTMTS', 'REVISED', 'BUDGET', 'YTD',
                'EXPENDED', 'ENC/REQ', 'AVAILABLE', 'PCT', 'USED'}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def money(s):
    s = s.replace(',', '')
    neg = s.startswith('-') or s.endswith('-')
    v = Decimal(s.strip('-'))
    return -v if neg else v


def page_words(path):
    d = json.load(open(path))
    out = []
    for b in d['Blocks']:
        if b['BlockType'] != 'WORD':
            continue
        bb = b['Geometry']['BoundingBox']
        out.append({'top': bb['Top'], 'left': bb['Left'], 'right': bb['Left'] + bb['Width'],
                    'text': b['Text'], 'conf': b['Confidence']})
    return out


def rows_of(words):
    """Band words into rows. The band is half the page's own row pitch."""
    words = sorted(words, key=lambda w: w['top'])
    tops = sorted({round(w['top'], 4) for w in words})
    gaps = [b - a for a, b in zip(tops, tops[1:]) if b - a > 0.002]
    band = (statistics.median(gaps) / 2) if gaps else 0.003
    band = min(band, 0.0035)  # an account row and its figure row sit ~0.008 apart
    rows, cur = [], []
    for w in words:
        if cur and w['top'] - cur[0]['top'] > band:
            rows.append(sorted(cur, key=lambda w: w['left']))
            cur = []
        cur.append(w)
    if cur:
        rows.append(sorted(cur, key=lambda w: w['left']))
    return rows


def column_edges(all_rows):
    """Measure the seven right edges from the figures themselves."""
    rights = sorted(w['right'] for r in all_rows for w in r
                    if (MONEY.match(w['text']) or PCT.match(w['text'])) and w['left'] > 0.3)
    clusters, cur = [], [rights[0]]
    for x in rights[1:]:
        if x - cur[-1] > 0.02:
            clusters.append(cur)
            cur = []
        cur.append(x)
    clusters.append(cur)
    clusters = [c for c in clusters if len(c) > 20]
    edges = [statistics.median(c) for c in clusters]
    if len(edges) != 7:
        sys.exit('column edges: expected 7 clusters of figures, measured %d: %s'
                 % (len(edges), ['%.4f' % e for e in edges]))
    return edges


def place(row, edges):
    """Figures to columns by nearest right edge. Returns dict or None if a column collides."""
    vals = {}
    for w in row:
        t = w['text']
        if not (MONEY.match(t) or PCT.match(t)):
            continue
        i = min(range(7), key=lambda k: abs(edges[k] - w['right']))
        if abs(edges[i] - w['right']) > 0.012 or i in vals:
            return None
        vals[i] = w
    return vals


def parse(pdf):
    sha = sha256(pdf)
    pages = sorted(glob.glob(os.path.join(CACHE, sha, 'p*-text.json')))
    if not pages:
        sys.exit('%s: no Textract text reads cached for sha256 %s' % (pdf, sha[:12]))
    per_page = []
    for p in pages:
        n = int(re.search(r'p(\d+)-text', p).group(1))
        per_page.append((n, rows_of(page_words(p))))
    edges = column_edges([r for _, rows in per_page for r in rows])

    accounts, totals, residue, meta = [], [], [], {}
    pending = None          # an account row waiting for its figures
    org = obj = None
    low_conf = []
    noise = []
    minus_joined = []
    for n, rows in per_page:
        for row in rows:
            texts = [w['text'] for w in row]
            line = ' '.join(texts)
            for w in row:
                if w['conf'] < 90:
                    low_conf.append((n, w['text'], round(w['conf'], 1)))
            top = row[0]['top']
            if top < 0.13 or top > 0.54 and line.startswith(('Report generated', 'User:', 'Program ID:')):
                m = re.search(r'FOR (\d{4}) (\d{1,2})', line)
                if m:
                    meta.setdefault('for', (m.group(1), m.group(2)))
                continue
            if set(texts) <= HEADER_WORDS:
                continue
            if re.match(r'^(Report generated|User:|Program ID:|Page \d+$)', line):
                continue
            # Textract sometimes returns a negative's minus sign as its own word, just left of the
            # figure and a hair lower (p190 of FY2025 prints `-.01`; the read gave `-` and `.01`).
            # Rejoin a lone '-' to a figure that starts within 0.012 of it on the same row.
            for w in list(row):
                if w['text'] == '-':
                    nxt = [v for v in row if MONEY.match(v['text']) and 0 <= v['left'] - w['right'] < 0.012]
                    if nxt and not nxt[0]['text'].startswith('-'):
                        nxt[0]['text'] = '-' + nxt[0]['text']
                        row.remove(w)
                        minus_joined.append((n, nxt[0]['text']))
            texts = [w['text'] for w in row]
            line = ' '.join(texts)
            if all(set(t) <= {'.', '-'} for t in texts):
                noise.append(n)      # a lone '.' or '-' under a row: nothing is printed there (checked by rendering p52)
                continue
            nums = [w for w in row if MONEY.match(w['text']) or PCT.match(w['text'])]
            words = [w for w in row if w not in nums]
            # a word sitting ON a figure column's right edge, right of the description, that is
            # not a well-formed figure: a misread figure, kept as such rather than as description
            bad = [w for w in words if w['left'] > 0.35 and re.fullmatch(r'[-\d.,%]+', w['text'])
                   and min(abs(e - w['right']) for e in edges) < 0.006]
            words = [w for w in words if w not in bad]
            if words and ACCOUNT.match(words[0]['text']):
                if pending:
                    residue.append((n, 'account with no figures before the next account: ' + pending['account']))
                pending = {'page': n, 'account': words[0]['text'],
                           'description': ' '.join(w['text'] for w in words[1:]),
                           'org': org, 'object': obj}
                if nums:  # figures on the same row
                    row = nums
                else:
                    continue
            if (nums or bad) and not words or (nums and words and pending and all(w['left'] > 0.4 for w in words)):
                # a figure row; stray description words to the right belong to the pending account
                vals = place(nums, edges)
                if vals is None or len(vals) + len(bad) < 6:
                    residue.append((n, 'figure row not placeable: ' + line))
                    continue
                if pending is None:
                    residue.append((n, 'figures with no account: ' + line))
                    continue
                for b in bad:
                    i = min(range(7), key=lambda k: abs(edges[k] - b['right']))
                    if i < 6 and i not in vals:
                        pending.setdefault('misread', []).append((COLS[i], b['text']))
                if words:
                    pending['description'] = (pending['description'] + ' ' +
                                              ' '.join(w['text'] for w in words)).strip()
                for i, c in enumerate(COLS):
                    pending[c] = money(vals[i]['text']) if i in vals else None
                pending['pct'] = vals[6]['text'] if 6 in vals else ''
                pending['figures_page'] = n
                accounts.append(pending)
                pending = None
                continue
            if words and words[0]['text'] == 'TOTAL':
                vals = place(nums, edges) or {}
                name = ' '.join(w['text'] for w in words[1:])
                rec = {'page': n, 'name': name}
                for i, c in enumerate(COLS):
                    rec[c] = money(vals[i]['text']) if i in vals else None
                totals.append(rec)
                continue
            if words and not nums and re.match(r'^[A-Za-z]?\d{4,8}$', words[0]['text']):
                # 4 digits: the fund. 6 bare digits: an object. Anything else -- 5 digits, 7 or 8,
                # or a letter-prefixed school org such as `S0011742` or `s2044312` -- is an org.
                code = words[0]['text']
                name = ' '.join(w['text'] for w in words[1:])
                if re.fullmatch(r'\d{6}', code):
                    obj = (code, name)
                elif not re.fullmatch(r'\d{4}', code):
                    org = (code, name)
                    obj = None
                continue
            if words and words[0]['text'].upper() == 'GRAND' and nums:
                vals = place(nums, edges) or {}
                rec = {'page': n, 'name': 'GRAND TOTAL'}
                for i, c in enumerate(COLS):
                    rec[c] = money(vals[i]['text']) if i in vals else None
                totals.append(rec)
                continue
            if line.strip() and n < len(per_page) - 2:
                residue.append((n, 'unclassified: ' + line))
    if pending:
        residue.append((pending['page'], 'account with no figures at end: ' + pending['account']))
    meta['noise_rows'] = len(noise)
    meta['minus_joined'] = minus_joined
    repair(accounts)
    return sha, edges, accounts, totals, residue, meta, low_conf


def repair(accounts):
    """A misread figure is recovered ONLY from an identity the row prints about itself, and only
    when the recovered value uses exactly the characters that were read (a transposition, as in
    `04.` for `.04`). Anything else stays blank and fails the check."""
    for a in accounts:
        for col, raw in a.get('misread', []):
            if a.get(col) is not None:
                continue
            if col == 'available' and None not in (a['revised'], a['expended'], a['encumbered']):
                v = a['revised'] - a['expended'] - a['encumbered']
            elif col == 'revised' and None not in (a['original'], a['transfers']):
                v = a['original'] + a['transfers']
            elif col == 'original' and None not in (a['revised'], a['transfers']):
                v = a['revised'] - a['transfers']
            elif col == 'transfers' and None not in (a['revised'], a['original']):
                v = a['revised'] - a['original']
            elif col in ('expended', 'encumbered') and None not in (a['revised'], a['available']):
                other = 'encumbered' if col == 'expended' else 'expended'
                if a[other] is None:
                    continue
                v = a['revised'] - a['available'] - a[other]
            else:
                continue
            printed = (f'{abs(v):,.2f}').lstrip('0') or '.00'
            if sorted(printed.replace(',', '')) == sorted(raw.replace(',', '').replace('-', '')):
                a[col] = v
                a.setdefault('repaired', []).append('%s read %r, set %s by the row identity' % (col, raw, v))


def check(accounts, totals):
    fails = []
    for a in accounts:
        if None in [a[c] for c in COLS]:
            fails.append((a['page'], a['account'], 'a column is blank'))
            continue
        if a['original'] + a['transfers'] != a['revised']:
            fails.append((a['page'], a['account'], 'original + transfers != revised'))
        if a['revised'] - a['expended'] - a['encumbered'] != a['available']:
            fails.append((a['page'], a['account'], 'revised - expended - enc != available'))
    # Each object-level TOTAL closes the accounts since the previous TOTAL that named an object.
    # Walk in print order: accounts accumulate into an open group; a TOTAL whose figures equal
    # the open group's sum closes it. Higher rollups (org, fund) are checked against the sum of
    # every account printed since the previous rollup of the same name class -- recorded, not forced.
    return fails


# Corrections read off the RENDERED page, each with where. Never inferred.
DESCRIPTION_OVERRIDES = {
    # Textract returned Hebrew letters; the page prints CCLT AND CCL (FY2026 p248, FY2025 p247).
    '0100-3-300-2110-99-6-10-1-511033': 'CCLT AND CCL',
}

# Which archive document each PDF is. The PDFs stay private (every page prints the report
# user's MUNIS login); what is published is OUR reading, below.
DOCS = {
    'f4bb0303980bba712282a3d3fe71e7330cc7f7ef75db10f2053a7e050634c340':
        'sources/town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-all.pdf',
    '313b0e2e43d3d5cb89561a54ecc3c89f6b346bb5209ac3473ea18cee3e5b32f6':
        'sources/town-ledgers/expenses/glytdbud-expense-fy2025-p13-gf-all.pdf',
}
READING = os.path.join(ROOT, 'sources', 'data', 'munis-gf-p13-reading.csv')
READING_TOTALS = os.path.join(ROOT, 'sources', 'data', 'munis-gf-p13-reading-totals.csv')
REDACTIONS = os.path.join(ROOT, 'sources', 'data', 'redactions.csv')
LEDGER_FIELDS = ['doc_id', 'fy', 'period', 'fund', 'fund_name', 'funds_covered', 'account_type',
                 'level', 'dept', 'org', 'object', 'account', 'function', 'name',
                 'original', 'transfers', 'revised', 'expended', 'encumbered', 'available',
                 'pct_used', 'totals_only', 'suppress_zero', 'rounded_columns']


def cleaned(a):
    """The two corrections every published row gets: org codes in MUNIS's own upper case
    (Textract read `S2044312` as `s2044312` on 8 accounts; the p12 workbook prints them upper),
    and the declared description overrides."""
    org = (a['org'] or ('', ''))[0].upper()
    desc = DESCRIPTION_OVERRIDES.get(a['account'], a['description'])
    if any(ord(ch) > 127 for ch in desc):
        sys.exit('non-ASCII description with no override: %s %r' % (a['account'], desc))
    return org, desc


def publishable(sha):
    """The gate: redactions.csv must name our reading as the public copy of this raw."""
    for r in csv.DictReader(open(REDACTIONS, newline='', encoding='utf-8')):
        if r['raw_sha256'] == sha:
            return r['public_key'] == 'data/munis-gf-p13-reading.csv'
    return False


def publish(results):
    rows, tots = [], []
    for sha, accounts, grand, meta in results:
        if not publishable(sha):
            sys.exit('redactions.csv does not name data/munis-gf-p13-reading.csv as the public '
                     'copy of %s; nothing published (CLAUDE.md 13e)' % sha[:12])
        fy, period = meta['for']
        doc = DOCS[sha]
        for a in accounts:
            org, desc = cleaned(a)
            seg = a['account'].split('-')
            pct = a['pct'].rstrip('%')
            rows.append({'doc_id': doc, 'fy': fy, 'period': period, 'fund': seg[0],
                         'fund_name': 'GENERAL FUND', 'funds_covered': '', 'account_type': 'expense',
                         'level': 'account', 'dept': seg[2], 'org': org, 'object': seg[-1],
                         'account': a['account'], 'function': seg[3], 'name': desc,
                         **{c: str(a[c]) for c in COLS}, 'pct_used': pct, 'totals_only': 0,
                         'suppress_zero': 0, 'rounded_columns': ''})
        tots.append({'doc_id': doc, 'fy': fy, 'period': period, 'page': grand['page'],
                     **{c: str(grand[c]) for c in COLS}})
    with open(READING, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(READING_TOTALS, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['doc_id', 'fy', 'period', 'page'] + COLS)
        w.writeheader()
        w.writerows(tots)
    print('published %s (%d rows) and %s' % (os.path.relpath(READING, ROOT), len(rows),
                                             os.path.relpath(READING_TOTALS, ROOT)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    do_publish = '--publish' in sys.argv
    os.makedirs(OUT, exist_ok=True)
    results, refused = [], False
    for pdf in args:
        sha, edges, accounts, totals, residue, meta, low = parse(pdf)
        stem = os.path.splitext(os.path.basename(pdf))[0]
        print('== %s  sha256 %s  FOR %s' % (pdf, sha[:12], meta.get('for')))
        print('   column right edges: %s' % ' '.join('%.4f' % e for e in edges))
        print('   accounts %d, TOTAL lines %d, residue %d, words under 90%% confidence %d, '
              'empty dot rows %d, repaired by identity %d'
              % (len(accounts), len(totals), len(residue), len(low), meta['noise_rows'],
                 sum(1 for a in accounts if a.get('repaired'))))
        print('   minus signs rejoined to their figure: %d %s' % (len(meta['minus_joined']), meta['minus_joined'][:12]))
        for a in accounts:
            for r in a.get('repaired', []):
                print('   repaired p%s %s: %s' % (a['figures_page'], a['account'], r))
        fails = check(accounts, totals)
        for f in fails[:20]:
            print('   FAIL p%s %s: %s' % f)
        refused = refused or bool(fails) or bool(residue)
        sums = {c: sum((a[c] or 0) for a in accounts) for c in COLS}
        print('   sum of accounts: ' + '  '.join('%s %s' % (c, f'{sums[c]:,}') for c in COLS))
        last_fund = [t for t in totals if t['name'] in ('GENERAL FUND', 'GRAND TOTAL')]
        grands = [t for t in totals if t['name'] == 'GRAND TOTAL']
        if len(grands) != 1 or not all(grands[0][c] == sums[c] for c in COLS):
            refused = True
        else:
            results.append((sha, accounts, grands[0], meta))
        for t in last_fund[-3:]:
            ok = all(t[c] == sums[c] for c in COLS)
            print('   printed TOTAL %-13s p%-3d %s  -> %s' % (
                t['name'], t['page'], '  '.join(f'{t[c]:,}' if t[c] is not None else '-' for c in COLS),
                'TIES' if ok else 'does not tie'))
        for r in residue[:40]:
            print('   residue p%s: %s' % r)
        with open(os.path.join(OUT, stem + '.accounts.csv'), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['page', 'figures_page', 'repaired', 'org', 'org_name', 'object', 'object_name', 'account',
                        'description'] + COLS + ['pct'])
            for a in accounts:
                w.writerow([a['page'], a['figures_page'], '; '.join(a.get('repaired', [])), (a['org'] or ('', ''))[0], (a['org'] or ('', ''))[1],
                            (a['object'] or ('', ''))[0], (a['object'] or ('', ''))[1], a['account'],
                            a['description']] + [a[c] for c in COLS] + [a['pct']])
        with open(os.path.join(OUT, stem + '.totals.csv'), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['page', 'name'] + COLS)
            for t in totals:
                w.writerow([t['page'], t['name']] + [t[c] for c in COLS])
        with open(os.path.join(OUT, stem + '.residue.txt'), 'w') as f:
            for r in residue:
                f.write('p%s\t%s\n' % r)
            for r in low:
                f.write('p%s\tlow confidence\t%s\t%s\n' % r)
    if do_publish:
        if refused:
            sys.exit('a report failed a check; nothing published')
        publish(results)


if __name__ == '__main__':
    main()
