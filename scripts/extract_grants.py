"""The district's grant income, grant by grant, from its own presentations.

The budget documents show the general fund and nothing else -- rule 11. The presentations
do not: two of them carry a "Grants History" section naming every entitlement and
competitive grant with its amount, FY21 to FY24, and the FY27 presentation carries FY26
actual and FY27 anticipated. That is the only place in anything Lunenburg publishes where
the other funding streams are named and priced.

It matters because a general-fund line rising can mean the district grew or can mean a
grant stopped paying, and these pages are the only way to tell the two apart.

    python3 scripts/extract_grants.py
"""
import os, re, csv, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'sources/district-budget-page/text')
OUT = os.path.join(ROOT, 'sources/data/grants-history.csv')

# "* Special Education, 240 Grant  $   418,237" -- the leading stars are footnote markers
# naming which director administers it, and are kept because they say who owns the money.
LINE = re.compile(r'^(\*{0,4})\s*([A-Za-z][^$]{3,70}?)\s*\$\s*([\d,]+)\s*$')
YEAR = re.compile(r'^FY(\d{2})\s+(FEDERAL|STATE)\s+GRANTS', re.I)
ESSER = re.compile(r'^(ESSER\s*\d)\s+\$?\s*([\d,]+)', re.I)
OWNER = {'*': 'Director of Special Services',
         '**': 'Director of Teaching & Learning',
         '***': 'Director of Community School Programs',
         '****': 'Nursing Coordinator'}


def scan(path):
    rows, fy, kind = [], None, None
    for ln in open(path, encoding='utf-8', errors='replace'):
        t = ln.strip()
        # Each grants page re-declares its own year and kind, so the section is closed at
        # every page break. Without this the header leaks into the budget tables further
        # down the deck and a department total gets recorded as a state grant.
        if t.startswith('===PAGE'):
            fy = kind = None
            continue
        m = YEAR.match(t)
        if m:
            fy, kind = 2000 + int(m.group(1)), m.group(2).lower()
            continue
        e = ESSER.match(t)
        if e:
            rows.append(dict(fy='FY21-24', kind='federal', name=e.group(1).upper(),
                             amount=float(e.group(2).replace(',', '')), owner='',
                             doc=os.path.basename(path)))
            continue
        m = LINE.match(t)
        # No single grant Lunenburg receives is seven figures; anything that large in a
        # grants section is a total or a stray budget row.
        if m and fy and float(m.group(3).replace(',', '')) < 1_000_000:
            name = re.sub(r'\s+', ' ', m.group(2)).strip(' ,')
            rows.append(dict(fy=fy, kind=kind, name=name,
                             amount=float(m.group(3).replace(',', '')),
                             owner=OWNER.get(m.group(1), ''), doc=os.path.basename(path)))
    return rows


# One deck, deliberately.
#
# Several presentations carry grant pages and they overlap, disagree by small amounts, and
# lay federal and state out differently -- merging them produced duplicates and grants
# filed under the wrong kind. The FY25 update carries a consistent "Grants History"
# section, one page per year, FY21 to FY24, and that is what is read. A narrower source
# that is right beats a wider one that is not.
SOURCE = 'fy25-superintendent-39-s-budget-update.txt'


def main():
    rows = scan(os.path.join(TEXT, SOURCE))
    if not rows:
        print('no grant tables found'); return
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'kind', 'name', 'amount', 'owner', 'doc'])
        w.writeheader()
        for r in sorted(rows, key=lambda x: (str(x['fy']), x['kind'], -x['amount'])):
            w.writerow(r)
    import collections
    by = collections.defaultdict(float)
    for r in rows:
        by[(r['fy'], r['kind'])] += r['amount']
    print(f'{len(rows)} grant lines\n')
    print(f"{'FY':<10}{'federal':>13}{'state':>13}{'total':>13}")
    for fy in sorted({r['fy'] for r in rows}, key=str):
        f, s = by[(fy, 'federal')], by[(fy, 'state')]
        print(f'{str(fy):<10}{f:>13,.0f}{s:>13,.0f}{f+s:>13,.0f}')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
