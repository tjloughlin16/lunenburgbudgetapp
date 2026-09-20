#!/usr/bin/env python3
"""Stabilization fund balances, read off the annual reports and proved row by row.

    python3 scripts/extract_stabilization.py           # write sources/data/stabilization-balances.csv
    python3 scripts/extract_stabilization.py --check
    python3 scripts/extract_stabilization.py --fy 2020 --verbose

WHY THIS EXISTS. `report_trust_funds` holds 642 rows of this across FY2011-FY2025 and
twelve are reconciled to anything. The pages are photographs of a printed table and the
generic pass could not read them.

HOW IT READS THEM is in `read_trust_table.py`: measure the page's own rotation from its
figures and remove it, anchor each row on its fund, place figures by column POSITION
rather than by order, and name the columns from a layout READ off that year's printed
header rather than inferred from how many figures a row happens to carry.

WHAT MAKES IT TRUSTWORTHY is that nothing is trusted. Every row must satisfy two
identities the table itself states -- beginning plus activity equals ending cash, and
ending cash plus unrealised equals ending market. A row that fails is not written. These
are OCR readings and the cache visibly contains `S2,041,061.72` and `$1,968,108,91`; a
misread digit does not survive both checks.

THE LAYOUTS ARE HYPOTHESES AND THE IDENTITIES TEST THEM. Nine columns were read off
FY2014's header and proposed for four other years. FY2015 and FY2016 accepted it -- ten
to twelve rows a page close. FY2017 and FY2022 rejected it, one row and none, so their
headers differ and they wait for somebody to read them. That is the check working, not
failing: a wrong layout cannot make real arithmetic close.

COVERAGE IS PARTIAL AND SAYS SO. What is written here is proven. What is missing is
missing because no layout has been read for that year yet, or because the year's pages
defeat the reader entirely -- FY2012, FY2013, FY2023 and FY2025 show no table with enough
columns to be one. `--check` fails if the file drifts; it does not claim the series is
complete.
"""
import argparse
import csv
import io
import os
import re
import sys
import warnings

warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T            # noqa: E402
import read_trust_table as R      # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'stabilization-balances.csv')

FIELDS = ['fy', 'code', 'name', 'registry_name', 'name_disagrees', 'ending_cash',
          'ending_market', 'page', 'basis', 'document']


def registry():
    out = {}
    f = os.path.join(ROOT, 'sources', 'data', 'fund-owners.csv')
    if os.path.exists(f):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            if (r.get('code') or '').strip():
                out[r['code'].strip()] = (r.get('name') or '').strip()
    return out


def year_files():
    for f in sorted(os.listdir(OCR)):
        m = re.search(r'fy-(\d{4})-annual-town-report\.tsv$', f)
        if m:
            yield int(m.group(1)), os.path.join(OCR, f)


def extract(fy, path, verbose=False):
    boxes = T.read_boxes(path)
    pages = sorted({b['page'] for b in boxes
                    if 'STABILIZATION' in (b['text'] or '').upper()})
    # EVERY PAGE THAT PROVES A ROW, NOT THE BEST ONE.
    #
    # This used to score the pages and keep the winner, which assumed a year's
    # stabilization funds live on one table. They do not: the general Stabilization Fund
    # is in the main trust listing and the Zoning Incentive and Vehicle/Equipment funds
    # are in "TRUST & STABILIZATION FUNDS HELD BY OTHER BANKS", two pages apart. So
    # picking a winner meant every year could publish one table's funds and silently drop
    # the other's -- and it did: FY2018 lost its $1,740,279.81 general fund row to a page
    # carrying two smaller funds, purely because two beats one.
    #
    # There is no need to choose. A row is published because the document's own
    # arithmetic closes on it, and that test does not care which page it was printed on.
    found = {}
    for p in pages:
        pb = [b for b in boxes if b['page'] == p]
        rows, cols = R.rows(pb, fy)
        # THREE, NOT SIX. The six was a cheap stand-in for "is this a trust table",
        # written before the reader could test a layout against the document's own
        # arithmetic. It is now the thing that decides, and it is far stricter than a
        # column count: FY2019's "held by other banks" table survives OCR as five columns
        # -- two of the printed ones lose every figure -- and it still foots, row after
        # row. A page is kept because its figures add up, not because it is wide.
        if len(cols) < 3:
            continue
        proven = [r for r in rows if R.verify(r['cells'])[0]]
        for r in proven:
            if 'STABIL' not in (r['code'] + r['name']).upper():
                continue
            # ONE ROW PER FUND PER YEAR. The same table is sometimes printed twice in one
            # report -- a listing and a recap -- and a fund read off both must not appear
            # twice. Keyed on the account number where the page prints one and on the
            # name where it does not, and the stronger proof keeps the slot.
            key = r['code'] or ' '.join(r['name'].split()).upper()[:30]
            better = (R.verify(r['cells'])[1] == 'both identities hold',
                      len(r['cells']))
            if key not in found or better > found[key][0]:
                found[key] = (better, p, r)
    if not found:
        return [], 'no page proves a stabilization row'
    stab = [(p, r) for _, p, r in found.values()]
    if verbose:
        for p, r in sorted(stab):
            print('   page %d: %s' % (p, ' '.join(r['name'].split())[:40]))
    # THE DOCUMENT'S NAME WINS, and where the registry disagrees that is recorded rather
    # than resolved. Substituting the registry silently turned `ZONING INCENTIVE
    # STABILIZATION (TD BANKNORTH)` -- what FY2020 and FY2025 both print against 8129 --
    # into `playground fund`, which is what `fund-owners.csv` has for that code. One of
    # the two is wrong and this file is not the place to decide which; rule 13 says quote
    # the source, so the source is quoted and the conflict is a column.
    names = registry()
    return [dict(fy=fy, code=r['code'],
                 name=' '.join(r['name'].split()),
                 registry_name=names.get(r['code'], ''),
                 name_disagrees=('yes' if names.get(r['code']) and
                                 names[r['code']].split()[0].upper()
                                 not in r['name'].upper() else ''),
                 ending_cash=round(r['cells']['ending_cash'], 2),
                 # EMPTY WHERE THE PAGE PRINTS NONE, never the cash value copied across.
                 # FY2019's table carries no ENDING MARKET VALUE figure on any row, and a
                 # fund at cash and a fund whose market value we could not read must not
                 # come out of this file looking the same.
                 ending_market=(round(r['cells']['ending_market'], 2)
                                if 'ending_market' in r['cells'] else ''),
                 # THE BASIS IS WHAT THE CHECK ACTUALLY RETURNED. It was a constant
                 # string, written when both identities were the only way through, and it
                 # would now be stating two proofs for a row that has one.
                 page=page, basis=R.verify(r['cells'])[1],
                 document=os.path.relpath(path, ROOT)) for page, r in stab], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fy', type=int)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()

    rows, missing = [], []
    for fy, path in year_files():
        if a.fy and fy != a.fy:
            continue
        got, err = extract(fy, path, a.verbose)
        print('FY%d  %d proven' % (fy, len(got)))
        if err:
            missing.append('FY%d: %s' % (fy, err))
        rows += got

    rows.sort(key=lambda r: (r['fy'], r['code'] or 'zz', r['name']))
    s = io.StringIO()
    # `\n`, EXPLICITLY. csv.DictWriter defaults to \r\n, and reading the file back
    # without newline='' translates it to \n -- so --check compares \r\n against \n and
    # reports a freshly written file as stale, every time. check_generated.py earned
    # itself on its first run by finding this exact bug elsewhere in this repository.
    w = csv.DictWriter(s, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    out = s.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if out != cur:
            print('stabilization-balances.csv is stale', file=sys.stderr)
            return 1
        print('current: %d proven rows' % len(rows))
        return 0
    if not a.fy:
        open(OUT, 'w', encoding='utf-8', newline='').write(out)
        print('\nwrote %s — %d proven rows across %d year(s)'
              % (os.path.relpath(OUT, ROOT), len(rows), len({r['fy'] for r in rows})))
        if missing:
            print('years with no proven row yet (their header needs reading):')
            for m in missing:
                print('  ' + m)
    return 0


if __name__ == '__main__':
    sys.exit(main())
