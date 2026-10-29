#!/usr/bin/env python3
"""Keystone Educational Collaborative tuition rate sheets -> sources/data/keystone-tuition-rates.csv

    python3 scripts/extract_keystone_tuition.py          # write
    python3 scripts/extract_keystone_tuition.py --check  # fail if the CSV no longer reproduces

Keystone (formerly FLLAC Educational Collaborative) publishes one page a year: three
programmes, each with a Member / Nonmember / Out of State row for the school year, the day
rate and the extended year, and an Initial 45 Day Rate line. The PDFs are filed under
sources/peer-districts/ and their text sits beside them, written by pdf_kind.extract_text.

EVERY AMOUNT IS READ OFF THAT TEXT, NEVER TYPED HERE. `amount_as_printed` is the string as
the page prints it, typos included (FY24 prints `$82.294.20`); `amount` is that string with
the `$`, commas and `/day` removed. Where the printed string is not a well-formed number the
`note` says how it was read.

HOW EACH LAYOUT IS READ.
  * Digital pages (FY24 both versions, FY26, FY27): one line per row, `Member $a $b $c`, in
    the column order the heading line prints -- school year, Day Rate, extended year.
  * FY25 is a scan (pdf_kind: 1 image page) read by OCR, which emits each block's amounts in
    one fixed order: three school-year, Initial Member, three day, three extended, Initial
    Nonmember. That order was checked against the rendered page on 29 October 2026; a block
    that does not yield exactly eleven amounts is refused.

ONE CHECK, OURS, recorded per row and never used to change a value: the school-year rate
against 180 x the printed day rate. The sheet does not print 180; it is our assumption
about a school year, and the check column says so.
"""
import argparse
import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
OUT = os.path.join(SRC, 'data', 'keystone-tuition-rates.csv')
BASE = 'https://keystonecollaborative.org/wp-content/uploads/'

# (document key, publisher URL path, fiscal year, how its text was read)
DOCS = [
    ('peer-districts/keystone-tuition-rate-sheet-fy24-2023-04.pdf',
     '2023/04/FY24-Tuition-Rate-Sheet.pdf', 2024, 'text layer'),
    ('peer-districts/keystone-tuition-rate-sheet-fy24-2023-07.pdf',
     '2023/07/FY24-Tuition-Rate-Sheet-.pdf', 2024, 'text layer'),
    ('peer-districts/keystone-tuition-rate-sheet-fy25.pdf',
     '2024/05/FY25-Tuition-Rate-Sheet-.pdf', 2025, 'ocr'),
    ('peer-districts/keystone-tuition-rate-sheet-fy26.pdf',
     '2025/05/FY26-Tuition-Rate-Sheet-.pdf', 2026, 'text layer'),
    ('peer-districts/keystone-tuition-rate-sheet-fy27.pdf',
     '2026/05/FY27-Tuition-Rate-Sheet.pdf', 2027, 'text layer'),
]
PROGRAMS = ['Key Program', 'Keystone Academy',
            'Keystone Educational Alternative Elementary and Middle School']
TIERS = ['Member', 'Nonmember', 'Out of State']
FIELDS = ['fy', 'program', 'tier', 'rate_type', 'column_heading_as_printed',
          'amount_as_printed', 'amount', 'check', 'note', 'document', 'page',
          'publisher_url', 'publisher_filename', 'read_by']
MONEY = re.compile(r'\$[\d.,]+(?:/day)?')


def number(s):
    """`$82.294.20` -> ('82294.20', note). Only the separators are touched."""
    core = s.lstrip('$').replace('/day', '')
    note = ''
    if core.count('.') > 1:
        head, tail = core.rsplit('.', 1)
        note = 'printed %s; the first full stop read as a thousands separator' % s
        core = head.replace('.', '') + '.' + tail
    return core.replace(',', ''), note


def blocks(text):
    """Split the page into one text block per programme, in printed order."""
    flat = text.replace('Keystone Educational Alternative Julie Bragg, Program Administrator',
                        'Keystone Educational Alternative')
    flat = re.sub(r'Keystone Educational Alternative\s+Elementary and Middle School',
                  PROGRAMS[2], flat)
    starts = []
    for p in PROGRAMS:
        i = flat.find(p)
        if i < 0:
            raise SystemExit('programme heading %r not found' % p)
        starts.append(i)
    if starts != sorted(starts):
        raise SystemExit('programmes not in the expected order')
    return {p: flat[s:(starts[n + 1] if n + 1 < len(starts) else len(flat))]
            for n, (p, s) in enumerate(zip(PROGRAMS, starts))}


def headings(block):
    sy = re.search(r'\d\d/\d\d School Year', block)
    ext = re.search(r'\d{4} Extended Year', block)
    if not (sy and ext and 'Day Rate' in block):
        raise SystemExit('column headings not found in block:\n' + block[:300])
    return sy.group(0), 'Day Rate', ext.group(0)


def cells_digital(block):
    out = {}
    for tier in TIERS:
        m = re.search(r'^\s*%s\s+(\S+)\s+(\S+)\s+(\S+)\s*$' % re.escape(tier), block, re.M)
        if not m:
            raise SystemExit('row %r not found' % tier)
        out[tier] = list(m.groups())
    m = re.search(r'Initial 45 Day Rate:\s+Member:\s+(\S+)\s+Nonmember:\s+(\S+)', block)
    if not m:
        raise SystemExit('Initial 45 Day Rate line not found')
    return out, m.group(1), m.group(2)


def cells_ocr(block):
    a = MONEY.findall(block)
    if len(a) != 11:
        raise SystemExit('OCR block yields %d amounts, not 11:\n%s' % (len(a), block))
    out = {t: [a[i], a[4 + i], a[7 + i]] for i, t in enumerate(TIERS)}
    return out, a[3], a[10]


def rows():
    out = []
    for key, path, fy, how in DOCS:
        txt = os.path.join(SRC, os.path.splitext(key)[0] + '.txt')
        text = open(txt, encoding='utf-8').read()
        if '===PAGE 2===' in text:
            raise SystemExit('%s has more than one page; the reader assumes one' % key)
        for prog, block in blocks(text).items():
            heads = headings(block)
            cells, init_m, init_n = (cells_ocr if how == 'ocr' else cells_digital)(block)
            common = {'fy': fy, 'program': prog, 'document': key, 'page': 1,
                      'publisher_url': BASE + path,
                      'publisher_filename': path.rsplit('/', 1)[1], 'read_by': how}
            for tier in TIERS:
                vals = [number(v) for v in cells[tier]]
                for rt, head, raw, (amt, note) in zip(
                        ('school_year', 'day', 'extended_year'), heads, cells[tier], vals):
                    check = ''
                    if rt == 'school_year':
                        day = vals[1][0]
                        prod = round(float(day) * 180, 2)
                        check = '180 x day rate %s = %.2f: %s' % (
                            day, prod, 'ties' if abs(prod - float(amt)) < 0.005 else 'DOES NOT TIE')
                    out.append({**common, 'tier': tier, 'rate_type': rt,
                                'column_heading_as_printed': head,
                                'amount_as_printed': raw, 'amount': amt,
                                'check': check, 'note': note})
            for tier, raw in (('Member', init_m), ('Nonmember', init_n)):
                amt, note = number(raw)
                out.append({**common, 'tier': tier, 'rate_type': 'initial_45_day',
                            'column_heading_as_printed': 'Initial 45 Day Rate: %s:' % tier,
                            'amount_as_printed': raw, 'amount': amt, 'check': '',
                            'note': note})
    return out


def render(rs):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rs)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    body = render(rows())
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != body:
            print('stale: %s does not reproduce' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok: %s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    tmp = OUT + '.tmp'
    open(tmp, 'w', encoding='utf-8', newline='').write(body)
    os.replace(tmp, OUT)
    print('wrote %d rows to %s' % (body.count('\n') - 1, os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
