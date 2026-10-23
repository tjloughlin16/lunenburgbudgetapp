#!/usr/bin/env python3
"""DESE's federal entitlement allocations, every district, every fund code, every year held.

    python3 scripts/extract_dese_entitlements.py           # write the two CSVs
    python3 scripts/extract_dese_entitlements.py --check   # rebuild both; fail if either differs

Reads the pages `fetch_dese_entitlements.py` landed in `sources/state-dese/entitlements/`
(the NEWEST snapshot of each page) and writes:

  sources/data/dese-entitlement-allocations.csv   one row per fiscal year, fund code, district
  sources/data/dese-fund-codes.csv                 fund code -> DESE's own grant name

WHAT AN ALLOCATION IS. The amount DESE says a district may draw on a grant for that fiscal
year. It is not a receipt and it is not a spend -- what was drawn and spent is in the town's
ledger, and the two are never summed (rule 1's cousin: different stage, different quantity).

WHERE THE CHECK COMES FROM. The by-fund-code view (`view=code`) prints a District Name |
Amount table for every district and NO TOTAL, so a code page cannot be footed on its own
face. The by-district view (`view=district`) prints every grant one district received that
year and a `District Total` that foots. So the check is the cross-view one: for each
reconciliation district, the district page must foot to its own printed total, AND its line
items must equal exactly the set of that district's rows across every fund-code page for the
year -- same codes, same amounts, nothing missing from either side. A year where that fails
for any reconciliation district is REFUSED: nothing from it is written.

Every page is also checked to have answered the question asked: DESE's form falls back to
another fund code silently (`code=240` returns 0113), so the SELECTED year and code on the
page must be the ones requested.

DISTRICT CODES come from the `<select>` on the by-district pages, which lists every district
as `<option value="0162">Lunenburg</option>`. A name in a code page that is in no select we
hold gets an empty `district_code`, and the count is printed rather than hidden.
"""
import argparse
import csv
import hashlib
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'state-dese', 'entitlements')
OUT = os.path.join(ROOT, 'sources', 'data', 'dese-entitlement-allocations.csv')
CODES_OUT = os.path.join(ROOT, 'sources', 'data', 'dese-fund-codes.csv')
OPPORTUNITIES = os.path.join(ROOT, 'sources', 'data', 'dese-grant-opportunities.csv')

CODE_URL = 'https://www.doe.mass.edu/grants/entitlement-allocation.aspx?view=code&fy={fy}&code={code}'
DISTRICT_URL = 'https://www.doe.mass.edu/grants/entitlement-allocation.aspx?view=district&fy={fy}&code={code}'
GRANTS_URL = 'https://www.doe.mass.edu/grants/grants.aspx'

# The districts every year is reconciled against. NAMES, resolved to codes off DESE's own
# select, so no district number is typed here. Lunenburg is the subject; the other three
# are its neighbours and one large urban district, so a defect that shows only at scale
# (many grants, many rows) has a chance to show.
#
# FITCHBURG IS NOT ON THE LIST BECAUSE ITS NAME IS AMBIGUOUS: DESE's select carries two
# options both labelled `Fitchburg` (0097 and 5884), and a code page names districts only by
# label, so its rows cannot be attributed to either code. Groton-Dunstable stands in as a
# regional district. A name that resolves to more than one code is refused, not guessed.
RECONCILE = ('Lunenburg', 'Leominster', 'Worcester', 'Groton-Dunstable')

FIELDS = ['fy', 'fund_code', 'grant_name', 'district', 'district_code', 'amount',
          'source_url', 'sha256']
CODE_FIELDS = ['fund_code', 'name', 'name_fy', 'federal_or_state', 'funding_basis',
               'source_url']

NO_NAME = 'No fund name found'
# What the grid holds, as its only cell, when a code had no allocations that year.
EMPTY = 'No data found for the given search criteria'


class Refused(Exception):
    pass


def text(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()


def selected(page, name):
    sel = re.search(r'id="[^"]*' + name + r'".*?</select>', page, re.S)
    if not sel:
        return None
    m = re.search(r'<option selected="selected" value="([^"]+)"', sel.group(0))
    return m.group(1) if m else None


def options(page, name):
    """[(value, label)] of a select, in page order."""
    sel = re.search(r'id="[^"]*' + name + r'".*?</select>', page, re.S)
    if not sel:
        return []
    return [(v, text(t)) for v, t in
            re.findall(r'<option[^>]*value="([^"]+)"[^>]*>(.*?)</option>', sel.group(0), re.S)]


def money(s):
    """Whole dollars, or None where DESE prints the district with an EMPTY amount cell --
    Lanesborough and Williamstown in FY2019 on 0140 and 0240. Not zero: nothing is printed."""
    if s.strip() == '':
        return None
    m = re.fullmatch(r'\$(\(?)([\d,]+)\)?', s.replace(' ', ''))
    if not m:
        raise Refused('amount %r is not a dollar figure' % s)
    v = int(m.group(2).replace(',', ''))
    return -v if m.group(1) else v


def grid(page):
    """Rows of the results grid -- the table DESE names gvProfilesNavigation, never 'the last
    table', because an empty result still has the search form's table above it."""
    m = re.search(r'<table[^>]*id="[^"]*gvProfilesNavigation".*?</table>', page, re.S)
    if not m:
        return []
    out = []
    for tr in re.findall(r'<tr.*?</tr>', m.group(0), re.S):
        cells = [text(x) for x in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        if cells:
            out.append(cells)
    return out


def heading(page):
    m = re.search(r'Label1"><h2>(.*?)</h2>', page, re.S)
    return text(m.group(1)) if m else ''


def parse_code_page(page, fy, code):
    """(grant_name or '', [(district, amount)]) for one fund code and year."""
    if selected(page, 'ddlFiscalYear') != fy or selected(page, 'ddlFundcode') != code:
        raise Refused('code page %s FY%s answered for year %s code %s'
                      % (code, fy, selected(page, 'ddlFiscalYear'), selected(page, 'ddlFundcode')))
    h = heading(page)
    m = re.fullmatch(r'(\w{4})-(.*) (\d{4})', h)
    if not m or m.group(1) != code or m.group(3) != fy:
        raise Refused('code page %s FY%s is headed %r' % (code, fy, h))
    # Whitespace collapsed: the heading sometimes carries a trailing space before the year
    # (0274 FY2017, 0180 FY2021-FY2027) that the by-district page does not.
    name = re.sub(r'\s+', ' ', m.group(2)).strip()
    name = '' if name == NO_NAME else name
    rows = []
    for cells in grid(page):
        if cells == [EMPTY]:
            continue
        if len(cells) != 2:
            raise Refused('code page %s FY%s has a row of %d cells: %r' % (code, fy, len(cells), cells))
        rows.append((cells[0], money(cells[1])))
    names = [r[0] for r in rows]
    if len(set(names)) != len(names):
        raise Refused('code page %s FY%s names a district twice' % (code, fy))
    if rows and not name:
        raise Refused('code page %s FY%s has rows and no grant name' % (code, fy))
    return name, rows


def parse_district_page(page, fy, dcode):
    """(district name, {fund_code: (grant_name, amount)}), footed to its District Total."""
    if selected(page, 'ddlFiscalYear') != fy or selected(page, 'ddlFundcode') != dcode:
        raise Refused('district page %s FY%s answered for year %s district %s'
                      % (dcode, fy, selected(page, 'ddlFiscalYear'), selected(page, 'ddlFundcode')))
    name = dict(options(page, 'ddlFundcode')).get(dcode, '')
    body, total = {}, []
    for cells in grid(page):
        if cells == [EMPTY]:
            continue
        if len(cells) != 3:
            raise Refused('district page %s FY%s has a row of %d cells' % (dcode, fy, len(cells)))
        if cells[1] == 'District Total':
            total.append(money(cells[2]))
        else:
            if cells[0] in body:
                raise Refused('district page %s FY%s lists fund %s twice' % (dcode, fy, cells[0]))
            body[cells[0]] = (re.sub(r'\s+', ' ', cells[1]).strip(), money(cells[2]))
    if len(total) != 1:
        raise Refused('district page %s FY%s prints %d District Total rows' % (dcode, fy, len(total)))
    if any(a is None for _n, a in body.values()) or total[0] is None:
        raise Refused('district page %s FY%s prints a grant or total with no amount' % (dcode, fy))
    if sum(a for _n, a in body.values()) != total[0]:
        raise Refused('district page %s FY%s: grants sum to %d, the page prints a District Total of %d'
                      % (dcode, fy, sum(a for _n, a in body.values()), total[0]))
    return name, body


def district_codes(page):
    """{district name: set of codes} off a by-district page's select. A set, because two
    options can share a label (Fitchburg: 0097 and 5884)."""
    out = {}
    for v, label in options(page, 'ddlFundcode'):
        out.setdefault(label, set()).add(v)
    return out


def reconcile(fy, code_pages, district_pages):
    """Raise Refused unless every reconciliation district's by-district page equals its rows
    across the fund-code pages. `code_pages` {code: page}; `district_pages` {dcode: page}.
    Returns one-line notes: grant-name differences between the two views, and any fund code
    the form OFFERS for the year that has no page held.

    A CODE WITH NO PAGE IS NAMED, NOT HIDDEN, AND IT IS THE ONLY EXCEPTION. DESE answers
    `view=code&fy=2018&code=0240` -- IDEA, the largest grant Lunenburg gets -- with a 302 to
    its 500 error page, every time (22-23 October 2026). That is a defect on DESE's side and
    no retry fixes it. Refusing all of FY2018 for it would throw away nineteen pages that DO
    reconcile, so the comparison is made on every code that WAS served, the missing one is
    excluded from both sides and printed, and its allocations are simply not in the extract.
    Any OTHER disagreement refuses the year.
    """
    if not code_pages:
        raise Refused('FY%s has no fund-code page held' % fy)
    if not district_pages:
        raise Refused('FY%s has no by-district page to reconcile against' % fy)
    by_code = {c: parse_code_page(p, fy, c) for c, p in code_pages.items()}
    offered = {v for v, _l in options(next(iter(code_pages.values())), 'ddlFundcode')}
    missing = offered - set(code_pages)
    notes = ['FY%s %s: offered by the form, NO PAGE HELD (DESE did not serve it); excluded '
             'from the check and from the extract' % (fy, c) for c in sorted(missing)]
    for dcode, page in sorted(district_pages.items()):
        name, body = parse_district_page(page, fy, dcode)
        across = {}
        for c, (_g, rows) in by_code.items():
            for d, amt in rows:
                if d == name:
                    across[c] = amt
        printed = {c: a for c, (_n, a) in body.items() if c not in missing}
        for c in sorted(set(body) & missing):
            notes.append('FY%s %s: %s prints $%s for it on its by-district page, which no '
                         'code page can confirm' % (fy, c, name, format(body[c][1], ',')))
        if printed != across:
            only_d = sorted(set(printed) - set(across))
            only_c = sorted(set(across) - set(printed))
            diff = sorted(c for c in set(printed) & set(across) if printed[c] != across[c])
            raise Refused('FY%s %s (%s): by-district page and fund-code pages disagree -- '
                          'only on district page %s; only on code pages %s; amounts differ %s'
                          % (fy, name, dcode, only_d, only_c,
                             ['%s: %s vs %s' % (c, printed[c], across[c]) for c in diff]))
        for c, (gname, _a) in body.items():
            if c in by_code and by_code[c][0] and by_code[c][0] != gname:
                notes.append('FY%s %s: district page names it %r, code page %r'
                             % (fy, c, gname, by_code[c][0]))
    return notes


# ------------------------------------------------------------------ what is held on disk

NAME = re.compile(r'^(code|district)-(\w{4})-fy(\d{4})\.html$')


def held():
    """{filename: path of its NEWEST snapshot}. Snapshot folders are dated; later wins."""
    out = {}
    if not os.path.isdir(DOCS):
        return out
    for day in sorted(d for d in os.listdir(DOCS) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d)):
        for f in os.listdir(os.path.join(DOCS, day)):
            out[f] = os.path.join(DOCS, day, f)
    return out


def read(path):
    return open(path, 'rb').read().decode('utf-8', 'replace')


def build():
    pages = held()
    years = {}
    for f, p in pages.items():
        m = NAME.match(f)
        if m:
            years.setdefault(m.group(3), {'code': {}, 'district': {}})[m.group(1)][m.group(2)] = p
    rows, refused, notes, names = [], [], [], {}
    codes_by_name = {}
    for fy in sorted(years):
        for p in years[fy]['district'].values():
            for n, c in district_codes(read(p)).items():
                codes_by_name.setdefault(n, set()).update(c)
    for fy in sorted(years):
        cp = {c: read(p) for c, p in years[fy]['code'].items()}
        dp = {c: read(p) for c, p in years[fy]['district'].items()}
        try:
            notes += reconcile(fy, cp, dp)
        except Refused as e:
            refused.append((fy, str(e)))
            continue
        # A code the form offers and DESE would not serve (0240 FY2018): the by-district
        # pages we hold DO print it, footed to their own District Total, so those districts'
        # rows come from there, with that page as the source. Every other district's
        # allocation on that code is not in this extract.
        offered = {v for v, _l in options(next(iter(cp.values())), 'ddlFundcode')}
        for dcode in sorted(dp):
            dname, body = parse_district_page(dp[dcode], fy, dcode)
            path = years[fy]['district'][dcode]
            sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
            for code in sorted((offered - set(cp)) & set(body)):
                rows.append({'fy': fy, 'fund_code': code, 'grant_name': body[code][0],
                             'district': dname, 'district_code': dcode, 'amount': body[code][1],
                             'source_url': DISTRICT_URL.format(fy=fy, code=dcode), 'sha256': sha})
        for code in sorted(cp):
            gname, drows = parse_code_page(cp[code], fy, code)
            path = years[fy]['code'][code]
            sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
            if gname:
                names.setdefault(code, {})[fy] = gname
            for d, amt in sorted(drows):
                dc = codes_by_name.get(d, set())
                rows.append({'fy': fy, 'fund_code': code, 'grant_name': gname, 'district': d,
                             'district_code': next(iter(dc)) if len(dc) == 1 else '',
                             'amount': '' if amt is None else amt, 'source_url': CODE_URL.format(fy=fy, code=code),
                             'sha256': sha})
    rows.sort(key=lambda r: (r['fy'], r['fund_code'], r['district']))
    return rows, refused, notes, names, pages


def opportunities():
    """Rows of sources/data/dese-grant-opportunities.csv -- DESE's open-grants list
    (grants.aspx), fetched and extracted by fetch_dese_grants.py / extract_dese_grants.py.
    The only fetched page that states a funding TYPE (its `Type of Funding` column), and it
    lists only grants open on the day it was fetched, so most codes are not on it."""
    if not os.path.exists(OPPORTUNITIES):
        return []
    return list(csv.DictReader(io.open(OPPORTUNITIES, encoding='utf-8')))


def code_rows(names):
    """One row per fund code. A code on the allocation pages takes DESE's name from the
    newest year that names it. A code ONLY on the open-grants list takes that list's program
    name verbatim (it carries DESE's own FY prefix, e.g. `FY27 ...`) and its detail page."""
    types, extra = {}, {}
    for r in opportunities():
        for c in r['fund_code'].split():
            if re.fullmatch(r'\w{4}', c):
                types.setdefault(c, set()).add(r['funding'].strip().capitalize())
                extra.setdefault(c, r)
    out = []
    for code in sorted(set(names) | set(extra)):
        t = types.get(code, set())
        t = t.pop() if len(t) == 1 else ''
        basis = ("'Type of Funding' on DESE's open-grants list, " + GRANTS_URL) if t else \
            'not stated on any page fetched'
        if code in names:
            fy = max(names[code])
            out.append({'fund_code': code, 'name': names[code][fy], 'name_fy': fy,
                        'federal_or_state': t, 'funding_basis': basis,
                        'source_url': CODE_URL.format(fy=fy, code=code)})
        else:
            r = extra[code]
            out.append({'fund_code': code, 'name': r['program'], 'name_fy': '',
                        'federal_or_state': t, 'funding_basis': basis,
                        'source_url': r['detail_url']})
    return out


def render(fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode('utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, refused, notes, names, pages = build()
    if not rows:
        print('no allocation pages held under %s -- run fetch_dese_entitlements.py, or '
              'sync_archive.py --pull on a fresh clone' % os.path.relpath(DOCS, ROOT))
        return 1
    outs = {OUT: render(FIELDS, rows), CODES_OUT: render(CODE_FIELDS, code_rows(names))}
    nocode = len({r['district'] for r in rows if not r['district_code']})
    years = sorted({r['fy'] for r in rows})
    print('%d allocations, %d years (FY%s-FY%s), %d fund codes, %d districts; %d district names '
          'match no code in any select held'
          % (len(rows), len(years), years[0], years[-1], len({r['fund_code'] for r in rows}),
             len({r['district'] for r in rows}), nocode))
    for fy, why in refused:
        print('  REFUSED FY%s: %s' % (fy, why))
    for n in notes:
        print('  note: ' + n)
    if a.check:
        bad = [p for p, b in outs.items() if not os.path.exists(p) or open(p, 'rb').read() != b]
        for p in bad:
            print('STALE: %s does not reproduce' % os.path.relpath(p, ROOT))
        return 1 if bad or refused else 0
    for p, b in outs.items():
        tmp = p + '.tmp'
        open(tmp, 'wb').write(b)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 1 if refused else 0


if __name__ == '__main__':
    sys.exit(main())
