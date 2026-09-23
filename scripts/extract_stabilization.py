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
to twelve rows a page close. FY2017 and FY2022 rejected it, one row and none. That is the
check working, not failing: a wrong layout cannot make real arithmetic close.

AND FY2022'S REFUSAL WAS A LAYOUT WE HAD ALREADY READ AND COULD NOT REACH. It prints the
same FOURTEEN columns FY2023 does, and those were recorded -- but `LAYOUTS` is consulted
only after every candidate has failed, so a header known for one year was invisible to
the three others that print it. FY2022, FY2024 and FY2025 now name it, and FY2022 went
from none to seventeen rows on one page. Two refusals that looked alike are not alike:
one is a LAYOUT we had not read, and one is our INSTRUMENT failing on a page we can see
(rule 13c). FY2023 is the second kind -- the header is right, and Vision returns its
stabilization block as `5=5=2255225229`, so it closes only after a re-OCR.

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


def fund_keys(code, name):
    """Every identity a fund can be recognised by, because no single one survives.

    The account number is the best key and the scan loses it: FY2018's Zoning row prints
    `8129` and FY2019's prints nothing, so keying on the code alone made the same fund
    two funds and the carry-forward proof could not find last year's reading. The printed
    NAME survives where the code does not -- and it is truncated differently every year
    (`ZONING INCENTIVE STABILIZATION (TD BAN`, `... (TD |`), so the bank in brackets has
    to go before it can match.

    Rule 13c: the format changes year to year, so recognise a thing by several marks and
    accept any of them, rather than by one mark and report it missing.
    """
    keys = []
    if code:
        keys.append(code)
    n = ' '.join((name or '').split()).split('(')[0]
    n = ' '.join(w for w in n.split() if not w.isdigit()).strip().upper()
    if n:
        keys.append(n)
    return keys


def _basis(r, prior):
    """Which proof actually carried this row -- never a constant.

    A row proven by the prior year's ending cash must not claim the table's own identity:
    they establish different things, and the weaker one cannot check how the beginning
    balance splits between principal and earnings.
    """
    ok, why = R.verify(r['cells'])
    if ok:
        return why
    last = next((prior[k] for k in fund_keys(r['code'], r['name']) if k in prior), None)
    return R.verify_from_prior(r['cells'], last)[1]


def extract(fy, path, verbose=False, prior=None):
    prior = prior or {}
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
        # A ROW MAY BE PROVEN TWO WAYS. Ordinarily by the table's own identity; failing
        # that, by last year's PROVEN ending cash plus this year's activity -- see
        # verify_from_prior(). The second exists because a single scanned digit in
        # BEGINNING PRINCIPAL sinks an otherwise clean row, and the beginning balance is
        # a quantity the previous year's page already printed and proved.
        #
        # Rule 13c: a row that refuses is a statement about our reading, not about the
        # town. Before this, FY2019's general Stabilization Fund was reported as absent
        # because a 6 had been scanned as a 5.
        proven = []
        for r in rows:
            ok, _ = R.verify(r['cells'])
            if ok:
                proven.append(r)
                continue
            # NOT `p`: that is the page number of the loop this sits inside, and
            # shadowing it wrote a balance into the page column of every row.
            last = next((prior[k] for k in fund_keys(r['code'], r['name'])
                         if k in prior), None)
            ok2, _ = R.verify_from_prior(r['cells'], last)
            if ok2:
                proven.append(r)
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
        # SORT ON A KEY, never on the tuple. Two rows on one page fall through to
        # comparing the dicts themselves, which raises -- so `--verbose` crashed on
        # every year that proves more than one fund from a single page.
        for p, r in sorted(stab, key=lambda t: (t[0], t[1]['name'])):
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
                 # INTEREST IS NOT PUBLISHED FROM THESE TABLES, and the reason is
                 # worth keeping. The reader names a `net_earnings` column and the pages
                 # print one, so it looks extractable -- but a row is proved by the cash
                 # identity, and that identity is a SUM. A sum is blind to the order of
                 # its terms, so two different layouts of the same width both close it
                 # and the arithmetic cannot say which is right.
                 #
                 # It is not hypothetical. FY2025 page 37's vehicle row came out with
                 # `net_earnings` = $250,000.00 and `begin_earnings` = $93,687.39. The
                 # true reading is the other way round: $93,687.39 of interest and a
                 # $250,000 Town Meeting transfer -- a round number that is obviously a
                 # vote and not a yield, and the row proves identically either way.
                 #
                 # Publishing it would have put a transfer on a page about what the town
                 # EARNS, which is the difference between a choice and a yield. The
                 # ledger's `revenue` column is labelled by the accounting system and is
                 # where interest comes from instead; that it covers one year is a real
                 # limit and is registered as a gap rather than papered over.
                 # THE BASIS IS WHAT THE CHECK ACTUALLY RETURNED. It was a constant
                 # string, written when both identities were the only way through, and it
                 # would now be stating two proofs for a row that has one.
                 page=page, basis=_basis(r, prior),
                 document=os.path.relpath(path, ROOT)) for page, r in stab], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fy', type=int)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()

    rows, missing = [], []
    # OLDEST FIRST, so a year can be proven from the one before it. year_files() does not
    # promise an order and the carry-forward proof depends on one: FY2019's general fund
    # closes against FY2018's proven ending cash, which has to exist by then.
    prior = {}
    for fy, path in sorted(year_files()):
        if a.fy and fy != a.fy:
            continue
        got, err = extract(fy, path, a.verbose, prior)
        print('FY%d  %d proven' % (fy, len(got)))
        if err:
            missing.append('FY%d: %s' % (fy, err))
        rows += got
        # Carry this year's proven endings forward for the next year to lean on.
        for r in got:
            try:
                v = float(r['ending_cash'])
            except (TypeError, ValueError):
                continue
            for k in fund_keys(r['code'], r['name']):
                prior[k] = v

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
