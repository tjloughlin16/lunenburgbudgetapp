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
TEXT = os.path.join(ROOT, 'sources/district-budget/text')
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


PAGE = re.compile(r'^===PAGE (\d+)===')


def scan(path):
    rows, fy, kind, page = [], None, None, None
    for ln in open(path, encoding='utf-8', errors='replace'):
        t = ln.strip()
        # Each grants page re-declares its own year and kind, so the section is closed at
        # every page break. Without this the header leaks into the budget tables further
        # down the deck and a department total gets recorded as a state grant.
        #
        # The page number is kept as well. Every figure below is a claim about what a
        # public document says, and the person checking it needs to be told where to look
        # -- especially now that the district's own copy of this deck asks for a sign-in
        # and ours is the only one open.
        m = PAGE.match(t)
        if m:
            page = int(m.group(1))
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
                             page=page, doc=os.path.basename(path)))
            continue
        m = LINE.match(t)
        # No single grant Lunenburg receives is seven figures; anything that large in a
        # grants section is a total or a stray budget row.
        if m and fy and float(m.group(3).replace(',', '')) < 1_000_000:
            name = re.sub(r'\s+', ' ', m.group(2)).strip(' ,')
            rows.append(dict(fy=fy, kind=kind, name=name,
                             amount=float(m.group(3).replace(',', '')),
                             owner=OWNER.get(m.group(1), ''), page=page,
                             doc=os.path.basename(path)))
    return rows


# Every deck that carries grant pages, with the disagreements between them surfaced
# rather than merged away.
#
# Reading them all was tried, produced duplicates and federal grants filed as state ones,
# and was narrowed to one deck. This is the wider version done properly: each row records
# which document and page it came from, the federal/state split is decided by the grant's
# own number rather than by whichever header last appeared, and where two decks state
# different amounts for the same grant and year BOTH are kept and marked.
#
# A disagreement between two of the district's own presentations is a finding, not noise.
# The FY25 update is preferred where they conflict, because its Grants History pages are
# a deliberate retrospective rather than a figure quoted in passing.
PREFERRED = 'fy25-superintendent-39-s-budget-update.txt'

# Every row carries where it came from, because every row is a claim about a document.
# The district's own copy of this deck returned 401 on 29 August 2026 -- it asks for a
# Google sign-in -- so ours is the copy a resident can actually open, and the hash is how
# anybody with access confirms the two are the same file.
SOURCE_URL = ('https://drive.google.com/file/d/1yJNhIyBLVT8mu4GeJuQSjniKCPA41Oyq/view'
              '  [requires sign-in as of 29 Aug 2026]')
OUR_COPY = ('https://lunenburgbudgetproject.org/docs/district-budget/docs/'
            'fy25-superintendent-39-s-budget-update.pdf')
SHA256 = '9169e2700def0c1a2b6bebbc55d4e7f737ea5c3a7354657f4d804c017af5dc7c'


# Federal entitlement grants carry these numbers; state competitive ones carry those.
# Classifying on the grant's own number beats trusting the last header seen, which is how
# federal grants ended up filed as state in the first attempt.
FEDERAL_NOS = {'240', '262', '274', '305', '140', '309', '252', '115'}
STATE_NOS = {'719', '117', '105', '528', '718', '237'}
NUM = re.compile(r'\b(\d{3})\b')


def classify(name, header_kind):
    nums = set(NUM.findall(name))
    if nums & FEDERAL_NOS:
        return 'federal'
    if nums & STATE_NOS:
        return 'state'
    if re.search(r'\bESSER\b|\bTitle\b|\bIDEA\b|\bAARP\b', name, re.I):
        return 'federal'
    return header_kind


def main():
    rows = []
    for f in sorted(os.listdir(TEXT)):
        if f.endswith('.txt'):
            rows += scan(os.path.join(TEXT, f))
    for r in rows:
        r['kind'] = classify(r['name'], r['kind'])
        # ESSER is both listed against a year in some decks and totalled FY21-24 in
        # another, so it is marked and can be counted once. It also needs separating on
        # its own merits: it was one-time pandemic money, and mixing it into a
        # year-on-year grant series makes ordinary grants look like they collapsed.
        r['esser'] = int(bool(re.search(r'\bESSER\b', r['name'], re.I)))

    # Same grant, same year, two decks, two amounts.
    import collections
    key = lambda r: (str(r['fy']), re.sub(r'[^a-z0-9]', '', r['name'].lower())[:28])
    seen = collections.defaultdict(list)
    for r in rows:
        seen[key(r)].append(r)
    kept, flagged = [], 0
    for k, group in seen.items():
        amounts = {g['amount'] for g in group}
        if len(amounts) > 1:
            flagged += 1
            best = next((g for g in group if g['doc'] == PREFERRED), group[0])
            best = dict(best, disagreement='; '.join(
                f"{g['doc'].replace('.txt','')} p{g['page']}: ${g['amount']:,.0f}"
                for g in group))
            kept.append(best)
        else:
            kept.append(dict(group[0], disagreement=''))
    rows = kept
    print(f'{flagged} grants where two of the district\'s own decks disagree\n')
    if not rows:
        print('no grant tables found'); return
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'kind', 'name', 'amount', 'owner', 'page', 'doc',
                                   'esser', 'disagreement', 'source_url', 'our_copy', 'sha256'])
        w.writeheader()
        for r in sorted(rows, key=lambda x: (str(x['fy']), x['kind'], -x['amount'])):
            w.writerow({**r, 'source_url': SOURCE_URL, 'our_copy': OUR_COPY,
                        'sha256': SHA256})
    import collections
    by = collections.defaultdict(float)
    for r in rows:
        by[(r['fy'], r['kind'])] += r['amount']
    print(f'{len(rows)} grant lines\n')
    print(f"{'FY':<10}{'federal':>13}{'state':>13}{'ordinary':>13}{'ESSER':>13}")
    for fy in sorted({r['fy'] for r in rows}, key=str):
        f = sum(r['amount'] for r in rows
                if r['fy'] == fy and r['kind'] == 'federal' and not r['esser'])
        st = sum(r['amount'] for r in rows
                 if r['fy'] == fy and r['kind'] == 'state' and not r['esser'])
        e = sum(r['amount'] for r in rows if r['fy'] == fy and r['esser'])
        print(f'{str(fy):<10}{f:>13,.0f}{st:>13,.0f}{f+st:>13,.0f}'
              + (f'{e:>13,.0f}' if e else f"{'—':>13}"))
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
