#!/usr/bin/env python3
"""What stopped being funded — every school line that went to zero, and when.

    python3 scripts/build_stopped_funding.py            # write it
    python3 scripts/build_stopped_funding.py --check    # fail if it is stale

THE QUESTION, AND WHY IT SURVIVES A LIMIT THAT SINKS ITS NEIGHBOUR. `budget_figure`
carries stage='restated' — a closed year re-presented INSIDE a district budget book, by
the party that spent it. That is why /budget-vs-actual cannot settle over-budgeting before
FY2026: both sides of that comparison come out of the same document, and a document cannot
audit itself. This page asks something else. It asks what the district's own reporting
shows it STOPPED funding, year on year — and a restatement is a perfectly fair source for
a claim about what the district reports. The page says so in those words.

NOT ONE FIGURE IS TYPED INTO THE PAGE. Everything on /what-stopped-being-funded arrives
from the file this writes.

FIVE THINGS IT REFUSES TO WRITE ON, each guarding a join or a reading that could silently
produce a page about nothing:

  1. stage='restated' must exist and stage='actual' must NOT. The stage was renamed on
     7 September 2026 because the old name was read as the accounting system and produced
     a published claim that twelve years of school actuals existed. If the old name comes
     back, this stops.
  2. every fiscal year in the span must carry rows, and every series must be non-empty.
  3. the two AGGREGATE pseudo-lines the extractor produced — a GRAND TOTAL and a fund
     subtotal that were read as though they were budget lines — must both still be
     present, and are then excluded. If one is renamed away, this stops rather than
     silently summing a total in with the lines under it.
  4. the per-year totals published must equal the sum of the per-line values published.
  5. the rename pass must match SOMETHING. A rename detector that finds nothing looks
     exactly like a book with no renames in it, and this book has renames in it — rule 6
     exists because a line that goes to zero and reappears renamed produces a −100% rate
     that looks like a finding.

HOW A RENAME IS ESTABLISHED, AND WHY NOT BY LABEL. Fuzzy label matching proposed
'M.S. Special Ed Speech Pathologists' → 'E.S. Special Ed Speech Pathologists' at 0.97 —
two different schools. So the test here is arithmetic rather than textual: two line_keys
that share a fiscal year and carry the IDENTICAL value in every shared year where either
is non-zero are one line printed under two spellings. `Special Education Transp - System`
and `Special Education Transportation - System` agree to the dollar for FY2015, FY2016 and
FY2017. That is a fact about the figures, not a judgement about the words.

WHAT THIS CANNOT ESTABLISH, and the page carries all four:
  - a line ending is not a service ending. It can be a rename, a merge, a move to a grant,
    or a re-presentation of the whole book (rule 7).
  - dollars are not people. A guidance line disappearing is not a counsellor leaving.
  - a budget line is NET (rule 11). A line falling to zero can mean a grant took it over.
  - this is the district's own reporting, not the town's accounting system.
"""
import argparse
import collections
import csv
import difflib
import itertools
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/stopped-funding.json')
MINUTES = 'sources/meetings/text'

STAGE = 'restated'

# The two rows in `budget_figure` that are not budget lines. Both come out of the same
# athletics pages: a printed GRAND TOTAL and a fund subtotal, read by the extractor as
# though they were lines under it. They are excluded by NAME rather than by a heuristic on
# the word "total", and the generator refuses to run if either stops being present —
# because a silent exclusion that matches nothing and a silent exclusion that matches
# everything look identical in the output.
AGGREGATE_LABELS = ['GRAND TOTAL ATHLETICS', 'plus TOTAL Revolving Fund']

# A decline has to be large enough to be a decision rather than a rounding, and off a base
# big enough that a percentage means something. Both are OURS and are published in the
# payload so the page can state them rather than describe them.
DECLINE_FLOOR = 10_000.0     # the line's own peak must reach this
DECLINE_SHARE = 0.5          # ...and its recent level must be at or under half of it
DECLINE_TAIL = 2             # 'recent' is the mean of the last this many published years

# How alike two labels have to read before this project will say ONE MIGHT BE the other.
# Ours, and the page says so. Only used where no shared year exists to settle it
# arithmetically.
SPELLING_MATCH = 0.90

# What the money buys, from what the district's own label names. OURS, and said to be
# ours on the page. Order matters: the first pattern that matches wins, so the specific
# sits above the general.
BUYS = [
    ('Teaching and specialist staff',
     r'teacher|paraprofessional|para\b|speech|psychologist|social worker|counselor|'
     r'counsellor|nurse|librarian|principal|director|coordinator|department head|'
     r'master teacher|tutoring|therapist|pathologist'),
    ('Substitutes and stipends',
     r'substitut|\bsubs?\b|stipend|overtime|longevity|accompanist|advisor'),
    ('Professional development',
     r'prof development|professional dev|accreditation|curriculum adoption|conferenc|'
     r'dues|meetings'),
    ('Books, materials and supplies',
     r'textbook|workbook|periodical|library book|supplies|materials|instr\. materials|'
     r'audio visual|a\.v\.'),
    ('Equipment, repair and maintenance',
     r'equipment|repair|maint|furniture|recondition|custodial|grounds|fire safety'),
    ('Transportation', r'transportation|transp|bus'),
    ('Tuition and out-of-district', r'tuition|collaborative|placement'),
    ('Utilities, contracts and services',
     r'contracted|contractual|electricity|natural gas|fuel oil|heating|telephone|'
     r'software|lease|legal|insurance|advertis|classified ads|dumping|sewerage|'
     r'unemployment|services'),
]

# The school a line is named for, read off the district's own prefix. Everything that
# names no school is reported as naming no school rather than being assigned to one.
SCHOOLS = [
    ('High school', r'^(h\.?\s?s\.|high school)'),
    ('Middle school', r'^(m\.?\s?s\.?[\s.]|middle school)'),
    ('Elementary school', r'^(e\.?\s?s\.|elementary school)'),
    ('Primary school', r'^(p\.?\s?s\.|primary school)'),
    ('Kindergarten', r'^kindergarten'),
    ('ACE', r'^ace\b'),
    ('District wide', r'^(d\.?\s?w\.|district wide)'),
]

# What the town said. Rule 15a: for every category this page says stopped, search the
# meeting archive for what people said about that thing. The archive is 2025 onward, so
# most of what is on this page predates anything searchable — which is itself worth
# printing, and `searchable_from` says so.
QUOTES = [
    dict(key='guidance', board='finance-committee', date='2026-02-26', kind='minutes',
         doc='7673',
         quote='Ana Lockwood seeks information about guidance counselors. Dr. Jodi '
               'Fortuna states there are only guidance counselors at the high school.',
         why='Three of the four guidance counsellor lines stop appearing in the '
             'district’s book after FY2022 and the middle school line is still funded in '
             'FY2025. A budget line is not a filled post, and this is the two halves '
             'sitting side by side.'),
    dict(key='psychologist', board='finance-committee', date='2021-03-18',
         kind='minutes', doc='2083',
         quote='Covid relief money was used to hire a part- time school psychologist.',
         why='The single largest line on this page that went to a printed zero and stayed '
             'there is a school psychologist line. Five years later a board is told a '
             'school psychologist was hired with money from outside the budget book. Two '
             'facts, five years apart, about different posts; the page does not join '
             'them, and this is what a line at zero can look like from the other side.'),
    dict(key='prof-development', board='school-committee', date='2026-02-04',
         kind='minutes', doc='7634',
         quote='the remaining $17,000 will be dedicated to contracted professional '
               'development',
         why='Every PER-SCHOOL professional development line in the district’s book is '
             'printed at zero from FY2021 onward, while the district-wide line rises. '
             'In FY2026 the Superintendent reports professional development being paid '
             'for out of a DESE grant as well. Three facts side by side; nothing here '
             'says any one of them caused another.'),
    dict(key='social-workers', board='finance-committee', date='2026-02-26',
         kind='minutes', doc='7673',
         quote='Dr. Jodi Fortuna and the other presenters do not suggest cutting social '
               'workers.',
         why='Said in the same passage, in the same meeting, about the neighbouring line.'),
]

# The terms searched in the meeting archive for this page. RULE 2: the COUNTS are not
# here. A grep that finds nothing prints nothing, and nothing reads as "nobody said it" --
# so the denominator and the per-term counts are RUN by this generator, against the same
# archive `scripts/search_minutes.py` reads, and land in the payload. A count typed here
# would be a figure in prose, and the empty ones are exactly the figures somebody would
# fail to notice going stale.
SEARCHED = ['guidance counselor', 'professional development', 'department head',
            'tutoring', 'psychologist', 'school psychologist', 'adjustment counselor',
            'textbook']

# DESE'S OWN FIGURES, AS CORROBORATION AND NOT AS A JOIN. `dese_function_expenditure`
# splits every function category into GENERAL FUND and GRANTS/REVOLVING, FY2009-FY2025,
# collected by the state to its own definitions. That is the one thing the district's
# budget book structurally cannot show (rule 11): the book is the general fund and nothing
# else, so a line falling because a grant took it over and a line falling because the
# activity stopped are identical in it.
#
# THE GRAINS DO NOT JOIN, and this is deliberately not a join. A district budget line is
# not a DESE function code; `crosswalk` in this database is EMPTY on purpose, because the
# mapping is an inference and recording an inference as a mapping is how this project's
# worst errors happen. So each category below is set BESIDE a family of district lines and
# read at the category level only: does the state's independently-collected total for this
# kind of spending fall in the years the district's lines stop? The pairing is OURS and the
# page says so.
DESE_LEA = '01620000'
DESE_CATEGORIES = [
    ('PDEV', 'the professional development lines',
     'Five per-school professional development lines go to zero. Did professional '
     'development spending fall?'),
    ('GUID', 'the guidance counsellor lines',
     'Three of the four guidance counsellor lines stop appearing after the FY2022 '
     'boundary. Did guidance spending fall?'),
    ('MATL', 'the textbook, workbook and supplies lines',
     'The largest group of zeroings by count is books, materials and supplies. Did '
     'spending on materials fall?'),
]

GAP_KEYS = [
    ('money_out', 'Whether a school line that stops appearing in the district’s book '
                  'stopped being funded'),
    ('money_out', 'Which school lines stopped being funded in FY2023, FY2024 or FY2025'),
    ('people', 'Whether a budgeted position was filled'),
    ('money_out', 'What the schools actually spent, per line, in any year before FY2026'),
]


def fail(msg):
    sys.exit(f'REFUSING TO WRITE — {msg}')


def classify(patterns, label, default):
    low = label.lower()
    for name, pat in patterns:
        if re.search(pat, low):
            return name
    return default


# ------------------------------------------------------------------ read the series

def series(cx):
    rows = cx.execute(
        'SELECT stage, COUNT(*) n FROM budget_figure GROUP BY stage').fetchall()
    stages = {r['stage']: r['n'] for r in rows}
    if 'actual' in stages:
        fail("budget_figure carries stage='actual' again. That name was read as the "
             'accounting system once already and produced a published claim that twelve '
             "years of school actuals existed. The stage is 'restated'.")
    if not stages.get(STAGE):
        fail(f"budget_figure carries no stage={STAGE!r} rows")

    raw = cx.execute(
        'SELECT line_key, label, fy, value, doc_id, documents_disagree '
        'FROM budget_figure WHERE stage=?', (STAGE,)).fetchall()

    seen_aggregate = {r['label'] for r in raw} & set(AGGREGATE_LABELS)
    missing = [l for l in AGGREGATE_LABELS if l not in seen_aggregate]
    if missing:
        fail(f'the aggregate pseudo-lines {missing} are no longer in budget_figure under '
             'those names. They are printed TOTALS that the extractor read as lines, and '
             'they are excluded by name. If they have been renamed or removed, this '
             'exclusion is now either wrong or silently matching nothing.')

    kept = [r for r in raw if r['label'] not in AGGREGATE_LABELS]
    if not kept:
        fail('every row was excluded as an aggregate')
    return kept


def dese(cx, first_fy, last_fy):
    """The state's own figures for the categories this page's findings sit in.

    Refuses on three things, each of which would otherwise publish a corroboration that
    corroborates nothing: the table being absent, Lunenburg having no rows in a category
    the page names, and any row DESE's own reconciliation marks as not tying."""
    have = cx.execute("SELECT name FROM sqlite_master WHERE type='table' "
                      "AND name='dese_function_expenditure'").fetchone()
    if have is None:
        fail('dese_function_expenditure is not in the database — this page sets the '
             "state's independent fund split beside the district's book, and without it "
             'the corroboration section would render empty')
    out = []
    for code, family, question in DESE_CATEGORIES:
        rows = cx.execute(
            'SELECT fy, gen_fund, grants_revolving, total, reconciles, doc_id '
            'FROM dese_function_expenditure '
            "WHERE lea=? AND level='category' AND func_cat_code=? ORDER BY fy",
            (DESE_LEA, code)).fetchall()
        if not rows:
            fail(f'DESE has no Lunenburg rows for category {code} — the join matched '
                 'nothing, which looks exactly like the state publishing nothing')
        bad = [r['fy'] for r in rows if r['reconciles'] != 'yes']
        if bad:
            fail(f'DESE category {code} does not reconcile in {bad} — refusing to quote '
                 'a figure the extract itself says does not tie')
        desc = cx.execute('SELECT func_cat_desc FROM dese_function_expenditure '
                          "WHERE lea=? AND level='category' AND func_cat_code=? LIMIT 1",
                          (DESE_LEA, code)).fetchone()['func_cat_desc']
        pts = [dict(fy=r['fy'], gen_fund=round(r['gen_fund'], 2),
                    grants=round(r['grants_revolving'], 2), total=round(r['total'], 2))
               for r in rows]
        # Summarised over the SAME span as the district's own series, so the two are
        # like for like. The longer state series is published whole beneath it.
        over = [p for p in pts if first_fy <= p['fy'] <= last_fy]
        if not over:
            fail(f'DESE category {code} has no year in common with the district series')
        first, last = over[0], over[-1]
        out.append(dict(
            code=code, name=desc, family=family, question=question, points=pts,
            first_fy=first['fy'], last_fy=last['fy'],
            gen_fund_first=first['gen_fund'], gen_fund_last=last['gen_fund'],
            gen_fund_change=round(last['gen_fund'] - first['gen_fund'], 2),
            grants_first=first['grants'], grants_last=last['grants'],
            grant_share_last=(round(last['grants'] / last['total'], 4)
                              if last['total'] else None),
            grant_share_max=max(
                (round(p['grants'] / p['total'], 4) for p in over if p['total']),
                default=None),
            overlap_first_fy=first['fy'], overlap_last_fy=last['fy'],
            documents=sorted({r['doc_id'] for r in rows})))
    return out


def minutes_coverage():
    """How much of what the town HELD is actually published, per board per year.

    A search finding nothing in a year where 14% of meetings have minutes is not evidence
    that nobody discussed it, and this page makes claims about what was and was not said.
    So the coverage travels with them."""
    path = os.path.join(ROOT, 'sources/data/minutes-coverage.csv')
    if not os.path.exists(path):
        fail('sources/data/minutes-coverage.csv is not here — the page states how thin '
             'the meeting record is in places, and that cannot be typed')
    rows = [r for r in csv.DictReader(open(path, encoding='utf-8'))
            if r['board'] == 'School Committee']
    if not rows:
        fail('minutes-coverage.csv carries no School Committee rows — the coverage '
             'caveat would render with nothing behind it')
    years = sorted(int(r['year']) for r in rows)
    agendas = sum(int(r['agendas']) for r in rows)
    minutes = sum(int(r['minutes']) for r in rows)
    empty = sorted({int(r['year']) for r in rows if int(r['minutes']) == 0})
    # The town's listing gives more than one row for some board-years; a year is one
    # row here, summed, or the shares would be quoted twice.
    agg = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        agg[int(r['year'])][0] += int(r['agendas'])
        agg[int(r['year'])][1] += int(r['minutes'])
    per = [dict(year=y, agendas=a, minutes=m,
                share=round(m / a, 4) if a else None)
           for y, (a, m) in sorted(agg.items())]
    empty = [r['year'] for r in per if r['minutes'] == 0]
    thin = [r['year'] for r in per if r['share'] is not None and r['share'] < 0.5]
    return dict(board='School Committee', first_year=years[0], last_year=years[-1],
                agendas=agendas, minutes=minutes,
                share=round(minutes / agendas, 4) if agendas else None,
                years_with_none=empty, years_under_half=thin, per_year=per)


def searched():
    """Run each term against the meeting archive, and report the denominator too.

    Same index and same matching as `scripts/search_minutes.py`: the town's own
    `index.csv` for what was published, the extracted text for what can be read. Refuses
    if the archive is not here, because zero hits out of zero documents is the sentence
    this whole method exists to prevent."""
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here — the page states how many meeting '
             'documents were searched, and a search of nothing is not a search')
    rows = list(csv.DictReader(open(idx, encoding='utf-8')))
    readable, dates = [], []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, 'sources/meetings/text', stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
            if r.get('date'):
                dates.append(r['date'])
    if not readable:
        fail('no meeting document is readable — refusing to publish a count of what '
             'nobody said')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    out = []
    for term in SEARCHED:
        pat = re.compile(re.escape(term), re.I)
        out.append(dict(term=term,
                        documents=sum(1 for b in bodies if pat.search(b))))
    if not dates:
        fail('no meeting document carries a date — the page states how far back the '
             'archive reaches and that cannot be typed')
    return dict(terms=out, readable=len(readable), published=len(rows),
                first_date=min(dates), last_date=max(dates))


def build():
    if not os.path.exists(DB):
        fail(f'{os.path.relpath(DB, ROOT)} is not here — run scripts/build_db.py')
    cx = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    cx.row_factory = sqlite3.Row

    rows = series(cx)
    by = collections.defaultdict(dict)
    label = {}
    docs = collections.defaultdict(set)
    disagree = set()
    for r in rows:
        by[r['line_key']][r['fy']] = r['value']
        label[r['line_key']] = r['label']
        docs[r['fy']].add(r['doc_id'])
        if r['documents_disagree']:
            disagree.add((r['line_key'], r['fy']))

    years = sorted({r['fy'] for r in rows})
    span = list(range(years[0], years[-1] + 1))
    gapyears = [y for y in span if y not in years]
    if gapyears:
        fail(f'no rows at all for {gapyears} — the span is not continuous and every '
             'year-on-year comparison on this page assumes it is')
    first_fy, last_fy = years[0], years[-1]

    # --------------------------------------------------- coverage, year by year
    coverage = []
    for fy in years:
        vals = [by[k][fy] for k in by if fy in by[k]]
        coverage.append(dict(
            fy=fy, lines=len(vals), zeros=sum(1 for v in vals if v == 0),
            total=round(sum(vals), 2), documents=len(docs[fy])))
    for c in coverage:
        s = round(sum(by[k][c['fy']] for k in by if c['fy'] in by[k]), 2)
        if abs(s - c['total']) > 0.005:
            fail(f'the FY{c["fy"]} total published does not equal the lines published')

    # --------------------------------------------------- the zeroing events
    events = []
    for k, d in by.items():
        for fy in sorted(d):
            prev = d.get(fy - 1)
            if prev is None or prev <= 0 or d[fy] != 0:
                continue
            back = [y for y in sorted(d) if y > fy and d[y] > 0]
            events.append(dict(
                line_key=k, label=label[k], fy=fy, was=round(prev, 2),
                returned=bool(back), returned_fy=back[0] if back else None,
                returned_value=round(d[back[0]], 2) if back else None,
                buys=classify(BUYS, label[k], 'Everything else'),
                school=classify(SCHOOLS, label[k], 'Names no school')))
    if not events:
        fail('not one line goes from funded to a printed zero anywhere in the series — '
             'that is the whole subject of this page and it cannot be empty')
    events.sort(key=lambda e: (e['fy'], -e['was']))

    per_year = []
    for fy in years[1:]:
        e = [x for x in events if x['fy'] == fy]
        # A year of no events is not necessarily a year in which nothing stopped. The
        # book has to PRINT a zero for a zeroing to be visible, and the documents
        # restating FY2023 onward print almost none. So the count of printed zeros
        # travels beside every count of events, and the page draws a year with no
        # printed zeros as a year with no evidence rather than as a year with none.
        zeros_printed = sum(1 for x in by.values() if x.get(fy) == 0)
        per_year.append(dict(
            fy=fy, zeros_printed=zeros_printed,
            n=len(e), dollars=round(sum(x['was'] for x in e), 2),
            returned_n=sum(1 for x in e if x['returned']),
            returned_dollars=round(sum(x['was'] for x in e if x['returned']), 2),
            stayed_n=sum(1 for x in e if not x['returned']),
            stayed_dollars=round(sum(x['was'] for x in e if not x['returned']), 2),
            lines_both_years=sum(1 for x in by.values() if fy in x and fy - 1 in x)))

    # --------------------------------------------------- permanent printed zeros
    permanent = []
    for k, d in by.items():
        funded = [fy for fy in sorted(d) if d[fy] > 0]
        if not funded:
            continue
        last = funded[-1]
        after = [fy for fy in sorted(d) if fy > last]
        if after and all(d[fy] == 0 for fy in after):
            permanent.append(dict(
                line_key=k, label=label[k], last_funded_fy=last,
                last_funded=round(d[last], 2), zero_years=after,
                last_seen_fy=max(after),
                buys=classify(BUYS, label[k], 'Everything else'),
                school=classify(SCHOOLS, label[k], 'Names no school')))
    if not permanent:
        fail('no line goes to a printed zero and stays there')
    permanent.sort(key=lambda p: -p['last_funded'])

    # --------------------------------------------------- lines that stop appearing
    last_seen = {k: max(d) for k, d in by.items()}
    first_seen = {k: min(d) for k, d in by.items()}
    vanished = []
    for k, d in by.items():
        if last_seen[k] >= last_fy:
            continue
        vanished.append(dict(
            line_key=k, label=label[k], last_fy=last_seen[k],
            last_value=round(d[last_seen[k]], 2),
            buys=classify(BUYS, label[k], 'Everything else'),
            school=classify(SCHOOLS, label[k], 'Names no school')))
    vanished.sort(key=lambda v: (-v['last_fy'], -v['last_value']))
    vanished_by_year = []
    for fy in years[:-1]:
        v = [x for x in vanished if x['last_fy'] == fy]
        vanished_by_year.append(dict(fy=fy, n=len(v),
                                     dollars=round(sum(x['last_value'] for x in v), 2)))

    # --------------------------------------------------- renames, established by value
    pairs = []
    keys = sorted(by)
    for a, b in itertools.combinations(keys, 2):
        shared = [y for y in set(by[a]) & set(by[b]) if by[a][y] > 0 or by[b][y] > 0]
        if not shared:
            continue
        if not all(abs(by[a][y] - by[b][y]) < 0.005 for y in shared):
            continue
        older, newer = (a, b) if first_seen[a] <= first_seen[b] else (b, a)
        # A RENAME is one label handing over to another: the older line stops before the
        # newer one does. Where BOTH run to the same last year the pair is a TWIN --
        # two labels carrying the same figures side by side, which is a different fact
        # and is not evidence that anything was renamed. `H.S. Psychologist` and
        # `Middle School Psychologist` agree to the dollar for nine consecutive years and
        # both are still printed in the last one; nothing in the document says whether
        # that is one post printed twice or two posts paid identically.
        tier = 'rename' if last_seen[older] < last_seen[newer] else 'twin'
        pairs.append(dict(
            older=label[older], newer=label[newer],
            older_last_fy=last_seen[older], newer_first_fy=first_seen[newer],
            newer_last_fy=last_seen[newer],
            shared_years=sorted(shared), shared=len(shared),
            value=round(max(by[a][y] for y in shared), 2),
            tier=tier, basis='identical value in every shared year',
            strength='repeated' if len(shared) >= 2 else 'single'))

    # A SECOND kind, and a weaker one. The pairs above share a year, so the figures
    # settle it. Where a line stops and a differently-spelled one starts the year after,
    # there is no shared year and no arithmetic to appeal to -- only the words. These are
    # OURS and are candidates, and the page says so: normalised label similarity at or
    # above the threshold, the same school prefix, and the successor first printed after
    # the predecessor's last year. The school-prefix condition is not decoration: without
    # it the same measure proposes 'M.S. Special Ed Speech Pathologists' ->
    # 'E.S. Special Ed Speech Pathologists' at 0.97, which is two different schools.
    def flat(s):
        return re.sub(r'[^a-z]', '', s.lower())
    spelling = []
    for k in by:
        if last_seen[k] >= last_fy:
            continue
        for p2 in by:
            if p2 == k or first_seen[p2] <= last_seen[k]:
                continue
            if classify(SCHOOLS, label[p2], '') != classify(SCHOOLS, label[k], ''):
                continue
            r = difflib.SequenceMatcher(None, flat(label[k]), flat(label[p2])).ratio()
            if r < SPELLING_MATCH:
                continue
            spelling.append(dict(
                older=label[k], newer=label[p2], older_last_fy=last_seen[k],
                newer_first_fy=first_seen[p2], newer_last_fy=last_seen[p2],
                older_value=round(by[k][last_seen[k]], 2),
                newer_value=round(by[p2][first_seen[p2]], 2),
                similarity=round(r, 3), tier='spelling candidate',
                basis='label similarity, ours', strength='candidate'))
    spelling.sort(key=lambda p: -p['similarity'])
    if not spelling:
        fail('the spelling-candidate pass matched nothing. Three of the lines that stop '
             'at the FY2022 boundary reappear with a letter changed; a pass that finds '
             'none of them is broken.')
    if not pairs:
        fail('the rename pass matched nothing. Rule 6 exists because this book renames '
             'lines; a detector that finds none of them is broken, not a clean result.')
    pairs.sort(key=lambda p: (p['tier'] != 'rename', -p['value']))

    # --------------------------------------------------- fell and did not recover
    declines = []
    for k, d in by.items():
        if last_fy not in d:
            continue
        peak = max(d.values())
        if peak < DECLINE_FLOOR:
            continue
        tail = [d[y] for y in sorted(d)[-DECLINE_TAIL:]]
        recent = sum(tail) / len(tail)
        if recent > DECLINE_SHARE * peak:
            continue
        peak_fy = min(y for y in d if d[y] == peak)
        if peak_fy >= last_fy - 1:
            continue
        declines.append(dict(
            line_key=k, label=label[k], peak_fy=peak_fy, peak=round(peak, 2),
            recent=round(recent, 2), recent_years=sorted(d)[-DECLINE_TAIL:],
            fall=round(peak - recent, 2), fall_share=round(1 - recent / peak, 4),
            buys=classify(BUYS, label[k], 'Everything else'),
            school=classify(SCHOOLS, label[k], 'Names no school')))
    if not declines:
        fail('no line fell off its own peak and stayed down — the decline pass matched '
             'nothing')
    declines.sort(key=lambda x: -x['fall'])

    # --------------------------------------------------- the categorical cuts
    def cut(items, field, amount):
        agg = collections.Counter()
        n = collections.Counter()
        for it in items:
            agg[it[field]] += amount(it)
            n[it[field]] += 1
        return [dict(name=k, n=n[k], dollars=round(v, 2))
                for k, v in sorted(agg.items(), key=lambda kv: -kv[1])]

    zero_amount = (lambda e: e['was'])
    categories = dict(
        zeroed_by_buys=cut(events, 'buys', zero_amount),
        zeroed_by_school=cut(events, 'school', zero_amount),
        permanent_by_buys=cut(permanent, 'buys', lambda p: p['last_funded']),
        vanished_by_buys=cut(vanished, 'buys', lambda v: v['last_value']),
    )

    # --------------------------------------------------- the shape change
    # The single largest apparent mass ending in the series, measured rather than named:
    # the year at which most lines stop appearing, with the reported totals either side.
    worst = max(vanished_by_year, key=lambda v: v['n'])
    tot = {c['fy']: c['total'] for c in coverage}
    lines = {c['fy']: c['lines'] for c in coverage}
    shape = dict(
        fy=worst['fy'], next_fy=worst['fy'] + 1, lines_stopped=worst['n'],
        dollars=worst['dollars'],
        lines_before=lines[worst['fy']], lines_after=lines[worst['fy'] + 1],
        total_before=tot[worst['fy']], total_after=tot[worst['fy'] + 1],
        total_change=round(tot[worst['fy'] + 1] - tot[worst['fy']], 2),
        renames_across=sum(1 for p in pairs + spelling
                           if p['older_last_fy'] <= worst['fy'] < p['newer_first_fy']),
        documents_before=sorted(docs[worst['fy']]),
        documents_after=sorted(docs[worst['fy'] + 1]))

    # The years with no evidence at all — where nothing could go from funded to zero
    # because the book stopped printing zeros. Measured, not named.
    silent = [p['fy'] for p in per_year if p['n'] == 0]

    # --------------------------------------------------- what the town said
    said = []
    for spec in QUOTES:
        rel = f'{MINUTES}/{spec["board"]}/{spec["date"]}-{spec["kind"]}-{spec["doc"]}.txt'
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail(f'{rel} is not here — a quote on this page is attributed to a document '
                 'that is not in the archive')
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        # The extracted minutes carry a mangled ligature where the PDF had "ff"; compare
        # on the letters rather than on the rendering (rule 13 — quote the source).
        want = re.sub(r'\s+', ' ', spec['quote'])
        if want not in text:
            fail(f'the quote attributed to {spec["board"]} {spec["date"]} is no longer in '
                 f'{rel} — quote the source, never your rendering of it')
        said.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'],
            cite=f'/docs/{rel.replace("sources/", "")}',
            town=f'https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/'
                 f'_{spec["date"][5:7]}{spec["date"][8:10]}{spec["date"][:4]}-'
                 f'{spec["doc"]}'))

    # The two line families a meeting quote is about, because a reader has to be able to
    # see the series the sentence sits beside. Selected on the district's own naming, and
    # each family refuses to be empty: a quote rendered above a chart of nothing is worse
    # than no quote.
    def family(match):
        out = []
        for k in sorted(by, key=lambda k: -max(by[k].values())):
            if not match(k):
                continue
            out.append(dict(
                line_key=k, label=label[k],
                points=[dict(fy=fy, value=round(by[k][fy], 2)) for fy in sorted(by[k])],
                first_fy=first_seen[k], last_fy=last_seen[k],
                last_value=round(by[k][last_seen[k]], 2),
                last_funded_fy=max([fy for fy in by[k] if by[k][fy] > 0], default=None)))
        return out

    guidance = family(lambda k: 'guidance counselor' in k)
    if not guidance:
        fail('no guidance counsellor line matched — the section quoting the '
             'Finance Committee about guidance counsellors would render with no series')
    prof_dev = family(lambda k: k.startswith('prof development'))
    if not prof_dev:
        fail('no professional development line matched — the section quoting the School '
             'Committee about professional development would render with no series')
    # The professional development lines split two ways in the district's own naming: one
    # per school, and one for the system. Summing them per year is what shows that the
    # per-school lines going to zero and the system line rising are the same years --
    # which is a measurement, and is NOT a claim that one paid for the other.
    pd_school = [g for g in prof_dev if not g['line_key'].startswith(
        'prof development system')]
    pd_system = [g for g in prof_dev if g['line_key'].startswith(
        'prof development system')]
    if not pd_school or not pd_system:
        fail('the professional development lines no longer split into per-school and '
             'system — the section comparing the two would render one empty half')
    pd_split = []
    for fy in years:
        def tot(fam):
            return round(sum(next((p['value'] for p in g['points'] if p['fy'] == fy), 0.0)
                             for g in fam), 2)
        printed = [g for g in prof_dev if any(p['fy'] == fy for p in g['points'])]
        if not printed:
            continue
        pd_split.append(dict(fy=fy, per_school=tot(pd_school), system=tot(pd_system),
                             per_school_lines=len(pd_school), lines_printed=len(printed)))
    pd_zero_from = next(
        (r['fy'] for r in pd_split
         if r['per_school'] == 0
         and all(x['per_school'] == 0 for x in pd_split if x['fy'] >= r['fy'])
         and any(x['per_school'] > 0 for x in pd_split if x['fy'] < r['fy'])), None)
    if pd_zero_from is None:
        fail('the per-school professional development lines no longer go to zero and stay '
             'there — the section built on that is no longer describing the data')

    # --------------------------------------------------- the gap register
    gaps = []
    for side, what in GAP_KEYS:
        r = cx.execute('SELECT side, what, why FROM money_gaps WHERE side=? AND what=?',
                       (side, what)).fetchone()
        if r is None:
            fail(f'money_gaps has no row ({side}, {what!r}). This page quotes the '
                 'register by key; add the row to sources/data/money-gaps.csv and rebuild '
                 'the database rather than typing the limit into the page.')
        why, _, closes = r['why'].partition('— closes:')
        gaps.append(dict(side=r['side'], what=r['what'],
                         why=why.strip().rstrip('·').strip(),
                         closes=closes.strip() or None))

    hits = searched()
    state = dese(cx, first_fy, last_fy)
    coverage_minutes = minutes_coverage()
    source_docs = sorted({r['doc_id'] for r in rows})

    return dict(
        generated_by='scripts/build_stopped_funding.py',
        source='sources/data/lunenburg.db — budget_figure, stage=restated',
        stage=STAGE,
        stage_note='A closed year re-presented inside a district budget book, by the '
                   'party that spent it. Not the town’s accounting system.',
        span=dict(first_fy=first_fy, last_fy=last_fy, years=len(years),
                  documents=len(source_docs)),
        documents=source_docs,
        excluded=AGGREGATE_LABELS,
        definitions=dict(
            zeroing='the line carries a value above zero in one year and a printed zero '
                    'in the next, with both years present in the book',
            returned='the same line carries a value above zero again in a later year',
            permanent='the line’s last funded year is followed only by printed zeros, '
                      'for as long as the line appears at all',
            vanished='the line stops appearing in the book altogether',
            rename='two differently-spelled lines carrying the identical value in '
                   'every fiscal year they share, where the older one stops first',
            twin='the same, where BOTH labels run to the last year of the series — two '
                 'labels on identical figures, which is not evidence of a rename',
            spelling_candidate='a line stops, and a line spelled almost the same for the '
                               'same school starts after it. Ours, and a candidate: '
                               'there is no shared year, so no arithmetic settles it',
            spelling_match=SPELLING_MATCH,
            decline=f'the line is still printed in the last year, its own peak reached '
                    f'at least ${DECLINE_FLOOR:,.0f}, and the mean of its last '
                    f'{DECLINE_TAIL} printed years is at or under '
                    f'{DECLINE_SHARE:.0%} of that peak',
            decline_floor=DECLINE_FLOOR, decline_share=DECLINE_SHARE,
            decline_tail=DECLINE_TAIL),
        coverage=coverage,
        totals=dict(
            lines=len(by),
            events=len(events),
            event_dollars=round(sum(e['was'] for e in events), 2),
            returned=sum(1 for e in events if e['returned']),
            returned_dollars=round(sum(e['was'] for e in events if e['returned']), 2),
            stayed=sum(1 for e in events if not e['returned']),
            stayed_dollars=round(sum(e['was'] for e in events if not e['returned']), 2),
            permanent=len(permanent),
            permanent_dollars=round(sum(p['last_funded'] for p in permanent), 2),
            vanished=len(vanished),
            vanished_dollars=round(sum(v['last_value'] for v in vanished), 2),
            declines=len(declines),
            decline_dollars=round(sum(d['fall'] for d in declines), 2),
            renames=sum(1 for p in pairs if p['tier'] == 'rename'),
            twins=sum(1 for p in pairs if p['tier'] == 'twin'),
            spelling_candidates=len(spelling),
            disagreeing_rows=len(disagree),
            biggest_permanent=permanent[0],
            biggest_decline=declines[0],
            silent_years=silent),
        per_year=per_year,
        vanished_by_year=vanished_by_year,
        events=events,
        permanent=permanent,
        vanished=vanished,
        renames=pairs,
        spelling_candidates=spelling,
        declines=declines,
        categories=categories,
        shape=shape,
        guidance=guidance,
        prof_development=prof_dev,
        prof_development_split=pd_split,
        prof_development_zero_from=pd_zero_from,
        said=said,
        dese=state,
        minutes_coverage=coverage_minutes,
        searched=hits['terms'],
        minutes=dict(readable=hits['readable'], published=hits['published'],
                     first_date=hits['first_date'], last_date=hits['last_date']),
        searchable_from=int(hits['first_date'][:4]),
        gaps=gaps,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {rel} is not what the database now produces. '
                  'Run scripts/build_stopped_funding.py.')
            return 1
        print(f'ok — {rel} reproduces from the database')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    t = d['totals']
    print(f'wrote {rel} — {t["events"]} zeroings across '
          f'FY{d["span"]["first_fy"]}-FY{d["span"]["last_fy"]} '
          f'(${t["event_dollars"]:,.0f}), {t["returned"]} of them funded again, '
          f'{t["permanent"]} lines zero and stayed zero, {t["renames"]} renames '
          f'established by value plus {t["spelling_candidates"]} spelling candidates, '
          f'{t["vanished"]} lines stop appearing; '
          f'{len(d["dese"])} DESE categories set beside them')
    return 0


if __name__ == '__main__':
    sys.exit(main())
