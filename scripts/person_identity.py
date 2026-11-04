#!/usr/bin/env python3
"""WHO IS WHO ACROSS A ROSTER: the one copy of the rule that decides whether two printed
names are one person.

Two generators need it and must not drift apart:

- `build_historical_report.py` ranks the longest runs on the school and town lists;
- `build_people.py` gives each person one page at /people/<slug>.

Before 3 November 2026 the people pages treated every printed form of a name as its own
person -- `Barbara S. Curtis`, `Mrs. Barbara S. Curtis` and `Barbara S. (Faulkner) Curtis`
were three pages -- while the historical report had already solved the problem for its
runs. The rule moved here so both read it.

THE RULE, all of it ours, chosen, and printed where it decides something:

1. `name_key`: a name with its titles (Mrs., Mr., Miss, Dr., Jr., Sr. ...), its middle
   initials and a bracketed maiden name dropped. `Barbara S. (Faulkner) Curtis` and
   `Barbara Curtis` share a key. A different first name never does: `Josh Tocci` and
   `Joshua Tocci` stay two (the one exception is `SAME_KEY`, below, each entry argued).
2. THE RUN RULE: a key is one person's run only while it keeps appearing. A run breaks when
   the name is absent from MORE THAN `MAX_ABSENT` consecutive rosters held.
3. `forms_disagree`: where the print itself tells two names apart that the key joined --
   both a Jr. and a Sr., or two different middle initials each printed at least twice --
   nothing is joined.
4. `CONFIRMED_DISTINCT`: what a person has told us, where the print cannot say.
"""
import collections
import re

# A NAME IS ONE PERSON'S RUN ONLY WHILE IT KEEPS APPEARING. A run breaks when the name is
# absent from MORE THAN this many consecutive roster editions we hold. Ours, chosen: it
# lets a teacher survive a roster that printed only part of a school (1993 and 1995 print
# a fraction of the usual names) and splits a name that vanishes for a decade -- which is
# the Nass case, eighteen years apart and two different jobs. It is printed on the page.
MAX_ABSENT = 2

# WHAT A PERSON HAS TOLD US ABOUT WHO IS WHO, where the print cannot say. Keyed by name_key;
# each entry is what was said, by whom (`by`, as the page attributes it) and when, and the
# page prints it AS a report -- no document held establishes it (rule 3). The run rule
# decides the ranking either way; this only replaces "cannot say" with the answer and its
# source. On the people pages a key named here is split at every break in its run, even
# where the printed form is identical on both sides.
CONFIRMED_DISTINCT = {
    # TJ, 2 November 2026: "there are 2 genevieve nass's! One is the mom, the other the daughter.
    # both worked for lunenburg." The run rule had already split them on the 1982-1998 absence.
    'genevievenass': dict(who='a mother and her daughter, both of whom worked for Lunenburg',
                          told='2 November 2026', by='the community'),
}

# A SHORT FORM OF A FIRST NAME, joined to the full form for ONE surname only, where the rosters
# themselves make the case. Never a general nickname table: `Josh` and `Joshua` stay two
# pages everywhere else. Each join is still subject to the run rule. Ours, each argued here.
SAME_KEY = {
    # T.C. Passios prints `Genevieve Nass` from 1999 to 2003 and `Gen Nass` from 2004, at the
    # same school, consecutive years; `Gen Nass` continues under Phys. Ed. and Specialist
    # Teacher to 2021, and `Genn Nass` is printed for 2012 and 2013 inside that run, in the
    # same post. The daughter in CONFIRMED_DISTINCT. Ours: no roster says they are one name.
    'gennass': 'genevievenass',
    'gennnass': 'genevievenass',
}

TITLES = {'mrs', 'mr', 'miss', 'ms', 'dr', 'jr', 'sr', 'ii', 'iii', 'rev', 'sister', 'ed'}
HONORIFICS = {'mrs', 'mr', 'miss', 'ms'}


def name_key(n, join=True):
    """The name with titles, middle initials and a bracketed maiden name dropped. `join`
    applies SAME_KEY; without it, the key of the letters actually printed."""
    n = re.sub(r'\([^)]*\)', ' ', n or '')
    t = [re.sub(r'[^a-z]', '', x) for x in re.split(r'[\s,.]+', n.lower())]
    k = ''.join(x for x in t if len(x) > 1 and x not in TITLES)
    return SAME_KEY.get(k, k) if join else k


def initials(n):
    t = [x for x in re.split(r'[\s,]+', re.sub(r'\([^)]*\)', ' ', n)) if x]
    return {x[0].lower() for x in t[1:-1] if re.fullmatch(r'[A-Za-z]\.?', x)}


def generations(n):
    return {x for x in re.split(r'[\s,.]+', n.lower()) if x in ('jr', 'sr')}


def has_honorific(n):
    t = re.split(r'[\s,.]+', (n or '').lower().strip())
    return bool(t) and t[0] in HONORIFICS


def forms_disagree(forms):
    """WHETHER THE PRINT ITSELF TELLS TWO NAMES APART that `name_key` joined. `name_key`
    drops middle initials and Jr./Sr., which is right for a name printed with and without
    its initial and wrong for a father and son: the town lists print `Charles Deming, Sr.`
    and `Charles Deming, Jr.` in the same years. A run is flagged when its printed forms
    carry BOTH Jr. and Sr., or two different middle initials each printed at least twice
    (once is an OCR slip: `Samuel 1. Costa`). `forms` is one entry per printing. Ours,
    chosen."""
    # A form's initials are compared as a SET: `Deborah A. H. Christen` printed eight times
    # is one name with two initials, not two initials that disagree (3 November 2026). Two
    # sets disagree when each is printed at least twice and neither contains the other.
    sets = collections.Counter(frozenset(initials(f)) for f in forms if initials(f))
    strong = sorted((x for x, k in sets.items() if k >= 2), key=sorted)
    gens = set().union(*(generations(f) for f in forms)) if forms else set()
    if {'jr', 'sr'} <= gens:
        return 'printed as both Jr. and Sr.'
    for i, x in enumerate(strong):
        for y in strong[i + 1:]:
            if not (x <= y or y <= x):
                return 'printed with %s middle initials' % ' and '.join(
                    c.upper() + '.' for c in sorted(x ^ y))
    return ''


def split_runs(years, held):
    """`years` (the years a name is printed) cut into runs at every absence from more than
    `MAX_ABSENT` consecutive years in `held`. Returns a list of sorted year lists."""
    ys = sorted(set(years))
    if not ys:
        return []
    held = sorted(set(held) | set(ys))
    cur, chunks = [ys[0]], []
    for y in ys[1:]:
        if len([h for h in held if cur[-1] < h < y]) > MAX_ABSENT:
            chunks.append(cur)
            cur = [y]
        else:
            cur.append(y)
    chunks.append(cur)
    return chunks


def name_runs(rows, year_of):
    """THE RUN RULE OVER ONE LIST. Every ranking on the historical report, school and town,
    and `build_town_rosters.py --runs`, goes through here, so they cannot drift apart.

    A name's run is its first to last year on the lists `rows` hold, broken when the name is
    absent from MORE THAN `MAX_ABSENT` consecutive years held. Returns (runs, by, held):
    runs sorted longest first, each with the rows inside it and `disagree` (see
    `forms_disagree`)."""
    held = sorted({year_of(r) for r in rows})
    by = collections.defaultdict(list)
    for r in rows:
        by[name_key(r['name'])].append(r)
    runs = []
    for k, rs in by.items():
        chunks = split_runs([year_of(r) for r in rs], held)
        for ch in chunks:
            inside = [h for h in held if ch[0] <= h <= ch[-1]]
            ents = sorted((r for r in rs if ch[0] <= year_of(r) <= ch[-1]),
                          key=lambda r: (year_of(r), int(r['page'] or 0), int(r.get('line') or 0)))
            forms = [e['name'] for e in ents]
            runs.append(dict(key=k, first=ch[0], last=ch[-1], span=ch[-1] - ch[0],
                             seen=len(ch), held=len(inside), split=len(chunks) > 1,
                             rows=ents, first_entry=ents[0], last_entry=ents[-1],
                             name=max(forms, key=lambda n: (forms.count(n), len(n))),
                             disagree=forms_disagree(forms)))
    runs.sort(key=lambda r: (-r['span'], -r['seen'], r['key']))
    return runs, by, held
