#!/usr/bin/env python3
"""The town's own wage list: every name it prints and what it paid them.

    python3 scripts/extract_gross_wages.py [--check]

Writes `sources/data/gross-wages.csv` -- fy, name, amount, and the department where the
town prints one.

TJ, 22 September 2026, on seeing the Council on Aging at eleven people: *"because when i
saw council on aging numbers, i was very surprised. but if some are part time, that number
is misleading."*

HE IS RIGHT AND THIS IS THE CORRECTIVE. The Council on Aging's eleven are real people and
nothing like eleven jobs: its MART van drivers were paid $1,539.37, $13,701.97 and
$24,119.96 in 2025, and its meal-site assistants $3,035.52 and $7,399.64. A headcount
counts the driver who works Tuesdays the same as the Director. The wage list is the only
thing the town publishes that can tell them apart.

WHAT IT IS AND IS NOT. It is GROSS WAGES paid in the year -- so it includes overtime,
police details, stipends and anyone who worked a single shift, and it is not salary, not
FTE and not a rate of pay. A low figure means a small amount of money was paid to that
person in that year; it does not say whether that is a part-time post, a mid-year start or
a retirement in September. Rule 11's warning runs the other way here too: this is what the
town PAID, which is not what a post COSTS once benefits are counted.

THE DEPARTMENT IS THE PROBLEM. The early lists tag each name with one -- `HOWARD, ERIN
FIRE` in FY2011, a `SCHOOL` heading in FY2016 -- and the later ones do not: FY2018 onward
print a name and an amount and nothing else. So a town-wide total is available for every
year the list reads, and a per-department total is only available where the town printed
the department, or where a name can be matched to a roster we hold.
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
OUT = os.path.join(ROOT, 'sources', 'data', 'gross-wages.csv')
FIELDS = ['fy', 'page', 'name', 'amount', 'department', 'as_printed']

# THE DOLLAR SIGN IS NOT ALWAYS THERE. FY2025 prints `$64,696.14` and FY2018 prints
# `13,757.44` bare, so a pattern anchored on `$` read FY2018's wage page as empty. The
# page is found from the contents rather than from the money, so dropping the anchor is
# safe here in a way it would not be if this were hunting for the page.
MONEY = re.compile(r'\$?\s?([\d,]+\.\d\d)')
HEAD = re.compile(r'gross wages|employee compensation|employee gross', re.I)
# The department, where the town tags it: appended to the name in the early lists.
DEPT_TAG = re.compile(r'\b(FIRE|POLICE|SCHOOL|DPW|LIBRARY|HIGHWAY|CEMETERY|WATER|SEWER'
                      r'|TOWN HALL|COA|SENIOR|BUILDING|PARK|RECREATION)\b$')
NOISE = re.compile(r'^(?:TOTAL|GRAND|PAGE|\d+)$', re.I)


def pages(fy):
    by, page = collections.defaultdict(list), None
    path = os.path.join(PAGES, 'FY%s.ocr.txt' % fy)
    if not os.path.exists(path):
        return {}
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        if page:
            by[page].append(re.sub(r'\s+', ' ', re.sub(r'^\s*\d+\|', '', line)).strip())
    return by


INDEX = os.path.join(ROOT, 'sources', 'data', 'report-index.csv')


def _index_pages(fy):
    """Where the town's contents page says the wage list is."""
    if not os.path.exists(INDEX):
        return []
    out = []
    for r in csv.DictReader(open(INDEX, encoding='utf-8')):
        if r['fy'] == fy and r['state'] == 'report' and HEAD.search(r['department']) \
                and r['pdf_from']:
            out += list(range(int(r['pdf_from']), int(r['pdf_to']) + 1))
    return sorted(set(out))


def wage_pages(by, fy):
    """Pages of the wage list, from the town's own contents page, then run on.

    THE FIRST VERSION GUESSED AND WAS COMPREHENSIVELY WRONG. It looked for pages dense in
    money, which is a description of every budget table in the book: FY2011 came back with
    39 `names` totalling $25.7 MILLION, because it was reading the appropriations summary.
    A wage figure is a person's pay and a budget figure is a department's, and nothing in
    the shape of the page tells them apart.

    The contents page says where the list is, and `extract_report_index.py` already reads
    it. The range it gives is often one page when the list runs six, so it is extended
    while the pages stay dense in SMALL money -- the test that does separate the two.
    """
    seed = _index_pages(fy)
    if not seed:
        seed = [p for p in sorted(by)
                if any(HEAD.search(t) for t in by[p][:8]) and _wagey(by[p])]
    if not seed:
        return []
    out, p = sorted(seed), max(seed) + 1
    while p in by and _wagey(by[p]):
        out.append(p)
        p += 1
    p = min(seed) - 1
    while p in by and _wagey(by[p]):
        out.insert(0, p)
        p -= 1
    return sorted(set(out))


def _wagey(lines):
    """Is this page a list of PEOPLE and pay, rather than a table of appropriations?

    Wages are small and there are hundreds of them. A budget page carries a few dozen
    figures and many of them are six and seven digits. Both are dense in money; only one
    is dense in money UNDER $250,000.
    """
    amts = [float(m.replace(',', '')) for t in lines for m in MONEY.findall(t)]
    if len(amts) < 25:
        return False
    small = sum(1 for a in amts if a < 250000)
    return small / len(amts) > 0.95


def parse_line(t):
    """(name, amount) pairs on one printed line, which carries TWO columns.

    SPLIT ON THE MONEY, NOT ON THE NAME. The list prints `ABRAHAM DAVID $64,696.14 LEGER
    VICTORIA $2,056.23` -- two people on one line -- and a pattern that tries to describe
    what a NAME looks like loses every compound surname on the page. The amounts are
    unambiguous, so each name is simply whatever text sits between the previous amount and
    the next one.
    """
    out, last = [], 0
    for m in MONEY.finditer(t):
        name = t[last:m.start()].strip(' .,-')
        last = m.end()
        name = re.sub(r'\s+', ' ', name).strip()
        if not name or NOISE.match(name) or len(name) < 4:
            continue
        dept = ''
        d = DEPT_TAG.search(name)
        if d:
            dept = d.group(1).title()
            name = name[:d.start()].strip(' ,')
        # A SURNAME ON ITS OWN IS STILL A PAYMENT. The list is set in two columns and the
        # right-hand column loses its given names in the line-level OCR -- `CAVACO QUINN
        # $68,275.47 NORMANDIN $58,020.26` -- so requiring two words threw away 47 lines
        # of one FY2025 page and about $5M of the town's payroll. The money is certain
        # even where the name is half read, and a town TOTAL needs only the money. A
        # partial name simply will not match a roster, which is the honest outcome.
        out.append((name, float(m.group(1).replace(',', '')), dept))
    return out


def read_year(fy):
    by = pages(fy)
    rows = []
    for p in wage_pages(by, fy):
        for t in by[p]:
            for name, amt, dept in parse_line(t):
                rows.append(dict(fy=fy, page=p, name=name, amount='%.2f' % amt,
                                 department=dept, as_printed=t[:160]))
    return rows


# ======================================================================================
# THE PAGES THE PAGE CACHE LOSES -- read from the Vision boxes instead
# ======================================================================================
#
# `sources/town-budget/pages/FY<year>.ocr.txt` is a fixed-width rendering of the Vision
# boxes, and everything above reads it. On two wage pages that rendering is empty of
# money where the boxes are full of it:
#
#     FY2011 page  98 -- 138 money boxes in the OCR, 0 in the page cache
#     FY2012 page 114 -- 133 money boxes in the OCR, 0 in the page cache
#
# The cache's FY2011 page 98 is not blank, which is worse than blank: it is that page
# rendered UPSIDE DOWN, so line 1 reads `L9'SLÉE$` and `T00 HOS`, which is `$338.27` and
# `SCHOOL` turned over. Nothing downstream could tell that from a page of bad OCR.
#
# RULE 13c: A MATCHER THAT FINDS NOTHING IS A STATEMENT ABOUT OUR INSTRUMENT. Two of
# them here -- the cache for both pages, and Vision itself for half of one -- and neither
# is a statement about the town, which printed both pages in full.
#
# What the boxes actually hold, which is the reason only one of the two pages publishes:
#
#   FY2011 page 98 is set in FOUR columns -- name, department, amount, then the same
#   again. Vision reads the RIGHT half completely (74 names against 75 amounts) and gives
#   up on the LEFT name column two thirds of the way down the page: 19 names against 63
#   amounts. So the right half pairs and most of the left half is amounts with nobody to
#   attach them to.
#
#   FY2012 page 114 has no names on it AT ALL. 338 boxes, of which 133 are money and the
#   rest are department words -- `SCHOOL`, `FIRE`, `SEWER`, `POLICE`. Both name columns
#   are unread. A department and an amount is not a wage row: it cannot be attributed to
#   anybody, it cannot be matched to a roster, and summing it would double-count against
#   the pages either side. That page is REFUSED.
#
# A WAGE PAGE PRINTS NO TOTAL -- not on any of the eight pages of the two lists, checked
# box by box -- so there is no identity to foot a row against, which is why every row in
# `report-gross-wages.csv` already carries `no check`. What stands in for it here is the
# PAIRING: a row is written only where one name and one amount sit in the same printed
# row on the same side of the page. An amount with two candidate names, or none, is
# counted and refused rather than attached to the nearest one.

OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT_REFUSED = os.path.join(ROOT, 'sources', 'data', 'gross-wages-refused.csv')
REFUSED_FIELDS = ['report_fy', 'document', 'page', 'subject', 'reason', 'evidence']

# fy -> document, pages. Kept explicit, and checked at run time against the cache: if a
# page here ever starts rendering, the script says so rather than reading it twice.
OCR_ONLY = {
    '2011': ('4117-fy-2011-annual-town-report.pdf', [98]),
    '2012': ('4118-fy-2012-annual-town-report.pdf', [114]),
}

OCR_MONEY = re.compile(r'^\$?\s?([\d,]+\.\d\d)$')
OCR_NAME = re.compile(r"^[A-Z][A-Za-z'\- ]{1,30},\s*[A-Z][A-Za-z'\- ]{1,30}$")
OCR_DEPT = re.compile(r'^(FIRE|POLICE|SCHOOL|DPW|LIBRARY|HIGHWAY|CEMETERY|WATER|SEWER'
                      r'|COA|SENIOR|BUILDING|PARK|RECREATION|TOWN HALL)$', re.I)


def ocr_boxes(doc, page):
    """One page of Vision boxes. Split on tabs -- csv may not be used on these files."""
    path = os.path.join(OCR, doc[:-4] + '.tsv')
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8', errors='replace') as fh:
        for i, line in enumerate(fh):
            f = line.rstrip('\n').split('\t')
            if i == 0 or len(f) < 7:
                continue
            try:
                p, x, y = int(f[0]), float(f[1]), float(f[2])
            except ValueError:
                continue
            if p == page:
                out.append({'x': x, 'y': y, 't': '\t'.join(f[6:]).strip()})
    return out


def _bands(boxes):
    """Printed rows, banded at HALF the page's own median row pitch -- rule 13b."""
    ys = sorted({round(b['y'], 4) for b in boxes}, reverse=True)
    gaps = sorted(a - b for a, b in zip(ys, ys[1:]) if 0.002 < a - b < 0.05)
    band = (gaps[len(gaps) // 2] / 2.0) if gaps else 0.005
    rows = []
    for b in sorted(boxes, key=lambda b: (-b['y'], b['x'])):
        if rows and abs(b['y'] - rows[-1][0]['y']) < band:
            rows[-1].append(b)
        else:
            rows.append([b])
    for r in rows:
        r.sort(key=lambda b: b['x'])
    return rows


def read_ocr_page(fy, doc, page, cache, refused):
    """Name-and-amount pairs off the boxes, and a refusal for everything that will not
    pair. The page is split at the middle because it is printed in two halves; a name in
    one half is never attached to an amount in the other.
    """
    boxes = ocr_boxes(doc, page)
    if not boxes:
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'the page has no Vision reading in the archive',
                        'evidence': '0 boxes'})
        return []
    cached_money = sum(len(MONEY.findall(t)) for t in cache.get(page, []))
    money = [b for b in boxes if OCR_MONEY.match(b['t'])]
    if cached_money > 5:
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'this page now renders in the page cache and is being '
                                  'read twice; take it out of OCR_ONLY',
                        'evidence': '%d money figures in the cache, %d in the boxes'
                                    % (cached_money, len(money))})
        return []
    rows, unpaired = [], 0
    for band in _bands(boxes):
        for lo, hi in ((0.0, 0.5), (0.5, 1.0)):
            half = [b for b in band if lo <= b['x'] < hi]
            names = [b for b in half if OCR_NAME.match(b['t'])]
            amts = [b for b in half if OCR_MONEY.match(b['t'])]
            depts = [b for b in half if OCR_DEPT.match(b['t'])]
            if len(names) == 1 and len(amts) == 1:
                rows.append(dict(fy=fy, page=page, name=names[0]['t'].strip(),
                                 amount='%.2f' % float(
                                     OCR_MONEY.match(amts[0]['t']).group(1).replace(',', '')),
                                 department=depts[0]['t'].title() if len(depts) == 1 else '',
                                 as_printed=' '.join(b['t'] for b in half)[:160]))
            elif names or amts:
                unpaired += 1
    if not rows:
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'no name on the page could be paired with an amount',
                        'evidence': '%d boxes, %d of them money, %d of them a personal '
                                    'name; the department words that remain (%s) cannot '
                                    'be attributed to anybody'
                                    % (len(boxes), len(money),
                                       sum(1 for b in boxes if OCR_NAME.match(b['t'])),
                                       ', '.join(sorted({b['t'].upper() for b in boxes
                                                         if OCR_DEPT.match(b['t'])})[:6]))})
    elif unpaired:
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'a half-row held a name without an amount, or an amount '
                                  'without a name, and was not guessed at',
                        'evidence': '%d half-rows paired, %d refused; Vision reads %d '
                                    'names against %d money figures on the page'
                                    % (len(rows), unpaired,
                                       sum(1 for b in boxes if OCR_NAME.match(b['t'])),
                                       len(money))})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, refused = [], []
    for f in sorted(glob.glob(os.path.join(PAGES, 'FY*.ocr.txt'))):
        m = re.search(r'FY(\d{4})\.ocr', f)
        if m:
            rows += read_year(m.group(1))
    for fy in sorted(OCR_ONLY):
        doc, want = OCR_ONLY[fy]
        cache = pages(fy)
        for page in want:
            rows += read_ocr_page(fy, doc, page, cache, refused)
    rows.sort(key=lambda r: (r['fy'], int(r['page']), r['name']))
    refused.sort(key=lambda r: (r['report_fy'], int(r['page']), r['reason']))
    if a.check:
        rc = 0
        old = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        if len(old) != len(rows) or any(
                any(str(r[k]) != o[k] for k in FIELDS) for r, o in zip(rows, old)):
            print('STALE %s' % OUT)
            rc = 1
        oldr = (list(csv.DictReader(open(OUT_REFUSED, encoding='utf-8')))
                if os.path.exists(OUT_REFUSED) else [])
        if len(oldr) != len(refused) or any(
                any(str(r[k]) != o[k] for k in REFUSED_FIELDS)
                for r, o in zip(refused, oldr)):
            print('STALE %s' % OUT_REFUSED)
            rc = 1
        return rc
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(OUT_REFUSED, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=REFUSED_FIELDS)
        w.writeheader()
        w.writerows(refused)
    for r in refused:
        print('  REFUSED FY%s page %s: %s -- %s'
              % (r['report_fy'], r['page'], r['reason'], r['evidence']))
    per = collections.Counter(r['fy'] for r in rows)
    tot = collections.defaultdict(float)
    for r in rows:
        tot[r['fy']] += float(r['amount'])
    print('%d wage rows across %d years' % (len(rows), len(per)))
    for fy in sorted(per):
        dep = len({r['department'] for r in rows
                   if r['fy'] == fy and r['department']})
        print('  FY%s  %4d names  $%12s  %s'
              % (fy, per[fy], format(int(tot[fy]), ','),
                 '%d departments tagged' % dep if dep else 'no department printed'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
