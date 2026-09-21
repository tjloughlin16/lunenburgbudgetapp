"""Money into and out of the stabilization funds, as the annual reports print it.

    python3 scripts/extract_stabilization_flows.py
    python3 scripts/extract_stabilization_flows.py --check

Writes `sources/data/stabilization-flows.csv`.

WHY NOT THE VOTES FILE. `town-meeting-votes.csv` has an article's SUBJECT and a quote, and
the quote is often the vote rather than the whole motion. Money leaves these funds inside
articles about something else -- the sewer enterprise budget, an omnibus transfer -- and
the clause that moves it is several lines below the part that got quoted. Classifying on
the subject found two withdrawals; reading the printed article text finds eleven.

TJ: *"we need to put 'What has come back out' in its own section, list the funds, the
pull, the year, and list EVERYTHING we know about. peopel wnat to know what thos eare
being used on and when."*

EVERY ROW KEEPS THE SENTENCE IT CAME FROM. That is the whole design. These are read out of
a scan with a regular expression, which is a weaker instrument than the identity-checked
table readers elsewhere in this archive, so the remedy is that nothing has to be taken on
trust: the `quote` column is the printed words, and a reader can disagree with our reading
of them without leaving the file.

AND THE AMBIGUOUS ONES ARE MARKED RATHER THAN DROPPED OR ASSERTED. Three kinds turned up
immediately and all three are still in the file with `confidence` saying so:

  `deposit-misread`  `from Sewer Enterprise Retained Earnings to the Reserve Capacity
                     Stabilization Fund` is money going IN. The pattern sees "from ...
                     stabilization" and cannot tell direction from shape alone.
  `combined`         `from the Sewer Reserve Capacity Stabilization fund and ...` -- the
                     figure covers more than one source and is not this fund's alone.
  `maybe-duplicate`  the same transaction printed in two consecutive reports, because each
                     year's warrant recites the year before. $20,962.40 appears three
                     times across FY2022 and FY2023.

A total is published only over `confidence = clear`, and the rest are visible beneath it.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'stabilization-flows.csv')

MONEY = r'\$[\d,]+\.\d{2}'
OUT_RE = re.compile(
    r'from\s+the\s+([A-Za-z/&\'. ]{4,60}?stabilization[A-Za-z ]{0,12}?)\s*'
    r'(?:account|fund)?\s*,?\s*(?:the\s+sum\s+of\s+)?(' + MONEY + r')'
    r'|transfer\s+(' + MONEY + r')\s+from\s+the\s+'
    r'([A-Za-z/&\'. ]{4,60}?stabilization[A-Za-z ]{0,12}?)\s*(?:account|fund)', re.I)

# `from X ... TO a stabilization fund` is a DEPOSIT wearing the words of a withdrawal.
INTO = re.compile(r'\binto\b|\bto\s+the\s+[^.;]{0,40}stabilization', re.I)

FIELDS = ['fy', 'page', 'fund', 'amount', 'direction', 'confidence', 'quote', 'document']

FUND_WORDS = [
    ('capital reserve', 'Sewer Capital Reserve Stabilization'),
    ('reserve capacity', 'Sewer Reserve Capacity Stabilization'),
    ('inflow', 'Inflow/Infiltration Stabilization'),
    ('infiltration', 'Inflow/Infiltration Stabilization'),
    ('health insurance', 'Health Insurance Stabilization'),
    ('opioid', 'Opioid Settlement Stabilization'),
    ('town building', 'Town Building Stabilization'),
    ('vehicle', 'Vehicle/Equipment Stabilization'),
    ('zoning', 'Zoning Incentive Stabilization'),
    ('special purpose', 'Special Purpose Stabilization'),
]


def fund_of(text):
    t = (text or '').lower()
    return next((lbl for w, lbl in FUND_WORDS if w in t), 'Stabilization Fund (general)')


def sentence(text, at, width=300):
    """The printed words around a match, so the row can be argued with.

    A FIXED WINDOW, NOT A SENTENCE. The first version split on the full stop and every
    quote came out starting mid-number -- `00; transfer from the Sewer Inflow/Infiltration
    Stabilization Fund the sum of $14,520.` -- because `$14,520.00` contains a full stop
    and these articles are nothing but amounts. It cut every quote at the decimal point of
    the figure it was quoting.

    Wide, too, and deliberately: TJ asked what the money was spent ON, and that is never
    in the clause that moves it. The purpose sits further along the article -- `to fund
    the FY2024 sewer enterprise budget`, `for the Police Department's Mental Health
    Co-Response programme` -- so the window has to be long enough to carry it.
    """
    lo = max(0, at - width // 3)
    hi = min(len(text), at + width)
    s = text[lo:hi]
    if lo:
        s = '\u2026' + s.split(' ', 1)[-1]
    if hi < len(text):
        s = s.rsplit(' ', 1)[0] + '\u2026'
    return ' '.join(s.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    rows = []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        fy = int(m.group(1))
        doc = os.path.relpath(f, ROOT)
        by_page = collections.defaultdict(list)
        for b in T.read_boxes(f):
            by_page[b['page']].append(b)
        for page, boxes in by_page.items():
            text = ' '.join(' '.join((b['text'] or '').split())
                            for b in sorted(boxes, key=lambda b: -b['y']))
            if 'stabiliz' not in text.lower():
                continue
            for mm in OUT_RE.finditer(text):
                src = (mm.group(1) or mm.group(4) or '').strip()
                amt = (mm.group(2) or mm.group(3) or '').replace('$', '').replace(',', '')
                try:
                    v = float(amt)
                except ValueError:
                    continue
                q = sentence(text, mm.start())
                conf = 'clear'
                # THE CAPTURED SOURCE GIVES IT AWAY. `from Sewer Enterprise Retained
                # Earnings TO THE Reserve Capacity Stabilization Fund` is money going in,
                # and the phrase this pattern captured as the source is the whole of
                # `Retained Earnings to the Reserve Capacity Stabilization`. A source
                # containing "to the" is not a source; it is a route, and the fund named
                # at the end of it is the destination.
                if re.search(r'\bto\s+the\b|\binto\b', src, re.I):
                    conf = 'deposit-misread'
                if re.search(r'stabilization\s+fund\s+and\b', src + ' and', re.I) or \
                        re.search(r'fund\s+and\s', src, re.I):
                    conf = 'combined'
                rows.append(dict(fy=fy, page=page, fund=fund_of(src), amount=round(v, 2),
                                 direction='out', confidence=conf, quote=q, document=doc))

    # THE SAME TRANSACTION, PRINTED TWICE. Each year's warrant recites the year before, so
    # an amount that appears in two consecutive reports for one fund is one withdrawal
    # seen twice. Marked, never silently merged -- two reports agreeing is also evidence.
    by_amt = collections.defaultdict(list)
    for r in rows:
        by_amt[(r['fund'], round(r['amount'], 0))].append(r)
    for group in by_amt.values():
        if len({r['fy'] for r in group}) > 1:
            for r in sorted(group, key=lambda r: r['fy'])[1:]:
                if r['confidence'] == 'clear':
                    r['confidence'] = 'maybe-duplicate'

    rows.sort(key=lambda r: (r['fy'], r['page'], -r['amount']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(rows)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/extract_stabilization_flows.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d flows across %d years' % (len(rows), len({r['fy'] for r in rows})))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    clear = [r for r in rows if r['confidence'] == 'clear']
    print('wrote %s -- %d rows, %d clear, $%s withdrawn'
          % (os.path.relpath(OUT, ROOT), len(rows), len(clear),
             format(sum(r['amount'] for r in clear), ',.2f')))
    for r in rows:
        print('  FY%d p%-4d %-38s $%12s  %s'
              % (r['fy'], r['page'], r['fund'][:38], format(r['amount'], ',.2f'),
                 r['confidence']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
