#!/usr/bin/env python3
"""Lunenburg Historical Report: what sixty-seven annual town reports say, 1959 to FY2025.

    python3 scripts/build_historical_report.py           # write the .md, the payload, the charts
    python3 scripts/build_historical_report.py --check   # fail if any output is stale

TJ, 30 October 2026: *"lets make a Lunenburg Historical Report that pulls some fun facts out
of these, mostly to prove they are ingested and we have the info from them. Thinking things
like: longest known employee, first town manager, etc etc, then something that pulls from
data across all years that is fun."*

SO THE PAGE IS A PROOF OF INGESTION FIRST AND A HISTORY SECOND. Every figure is read here,
on every run, from something the pipeline produced -- the extracted text of each report
(`sources/town-annual-reports/text/`), the school staff rosters
(`sources/data/staff-roster-entries.csv`) and the Textract tables (`sources/data/report-*.csv`).
Nothing is typed. If an extract changes, this page changes with it; if a passage it quotes
stops being found, the build REFUSES rather than printing the old sentence (CLAUDE.md
"a join that matches nothing looks exactly like data that is absent").

ONE PASS, FOUR OUTPUTS: the markdown (`/docs`, the PDF, agents that cannot run JavaScript),
the payload (`/data/historical-report.json`, which the page renders), and three SVGs that
stand in for the chart components in the markdown only (rule 7f).

THREE KINDS OF CLAIM ON THIS PAGE, AND THEY ARE KEPT APART (rule 7):

  * what a report PRINTS -- a tax rate, a vote count, a population. Quoted with edition
    and page.
  * what WE DERIVED -- a span between the first and last roster a name appears on. That is
    our arithmetic over a name match, and a name is not a person: one name below is printed
    against a cafeteria cook in 1961 and a gym teacher in 1999.
  * WHY something moved -- the tax-rate cliffs. Each sits beside a report saying the town
    revalued that year; the coincidence is shown, the report is quoted, and nothing here
    goes further than the report does.

DOLLARS ARE NOMINAL THROUGHOUT. The only price index this archive holds
(`sources/federal-bls/`, CPI-U Northeast) starts in 1990, so nothing from 1950 can be
adjusted with a cited index, and nothing is.
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import conclusions as C  # noqa: E402
from conclusions import conclusion, emit, figure  # noqa: E402
from build_stabilization_charts import (  # noqa: E402
    AXIS, FONT, GRID, INK, MUTED, PAD, SECOND, SURFACE, esc,
)

ID = 'historical-report'
TITLE = 'Lunenburg Historical Report'
OUT = os.path.join(ROOT, 'sources', 'analyses', ID + '.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', ID + '.json')
CHART_DIR = os.path.join(ROOT, 'sources', 'analyses', 'charts')
INDEX = os.path.join(ROOT, 'sources', 'town-annual-reports', 'index.csv')
DATA = os.path.join(ROOT, 'sources', 'data')
ROSTERS = os.path.join(DATA, 'staff-roster-entries.csv')

BLUE = '#184f95'
AMBER = '#e08214'

# A NAME IS ONE PERSON'S RUN ONLY WHILE IT KEEPS APPEARING. A run breaks when the name is
# absent from MORE THAN this many consecutive roster editions we hold. Ours, chosen: it
# lets a teacher survive a roster that printed only part of a school (1993 and 1995 print
# a fraction of the usual names) and splits a name that vanishes for a decade -- which is
# the Nass case, eighteen years apart and two different jobs. It is printed on the page.
MAX_ABSENT = 2
TITLES = {'mrs', 'mr', 'miss', 'ms', 'dr', 'jr', 'sr', 'ii', 'iii', 'rev', 'sister', 'ed'}

usd = C.usd
num = C.num


def rate(x):
    return '$%.2f' % x


# --------------------------------------------------------------------------------------
# The editions: one row per annual report, its text, its PDF, its sha256.
# --------------------------------------------------------------------------------------

def editions():
    out = {}
    with open(INDEX, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if not r['text'].endswith('.txt') or 'addendum' in r['text']:
                continue
            ed = int(re.search(r'(\d{4})', r['label']).group(1))
            out[ed] = dict(
                edition=ed, label=r['label'], fy=r['label'].startswith('FY'),
                text=os.path.join(ROOT, r['text']), pdf=r['local'],
                docs_url='/docs/' + r['local'][len('sources/'):],
                filename=os.path.basename(r['local']), sha256=r['sha256'],
                url=r['upstream'].split()[0] if r['upstream'] else '')
    if len(out) < 60:
        raise SystemExit('the annual-report index names %d editions; expected the 52 older '
                         'reports and the FY2011-FY2025 set. Refusing.' % len(out))
    return out


_PAGES = {}


def pages(ed):
    """{page number: text} for one edition. The numbers are the PDF's own page order --
    the same numbering the roster extract's `page` column uses."""
    if ed['edition'] not in _PAGES:
        txt = open(ed['text'], encoding='utf-8', errors='replace').read()
        parts = re.split(r'===PAGE (\d+)===', txt)
        _PAGES[ed['edition']] = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
    return _PAGES[ed['edition']]


def cite(ed, page):
    return dict(edition=ed['edition'], label=ed['label'], page=page,
                href='%s#page=%d' % (ed['docs_url'], page))


def link(c):
    name = c['label'].replace(' Annual Town Report', '')
    return '[%s report, p. %d](%s)' % (name, c['page'], c['href'])


def find(eds, year, pattern, what):
    """The page of `year`'s report holding `pattern`, and the matched text, whitespace
    normalised. REFUSES if it is not there: a quoted passage nothing can find is a quote
    this page must not print."""
    ed = eds[year]
    rx = re.compile(pattern, re.I | re.S)
    for p, body in sorted(pages(ed).items()):
        m = rx.search(body)
        if m:
            return dict(cite(ed, p), quote=' '.join(m.group(0).split()))
    raise SystemExit('%s: /%s/ is no longer found in the %d report. Refusing -- the page '
                     'would quote a passage the archive does not hold.' % (what, pattern, year))


# --------------------------------------------------------------------------------------
# 1. The fact page every edition opens with: tax rate, population, roads, government.
# --------------------------------------------------------------------------------------

MONEY = re.compile(r'\$\s*(\d{1,3})[.:,](\d\d)\b')


def fact_page(ed):
    for p, body in sorted(pages(ed).items()):
        if p > 15 and not ed['fy']:
            break
        if re.search(r'INCORPORATED', body, re.I) and re.search(r'TAX RATE', body, re.I):
            return p, body
    return None, None


def tax_rates(eds):
    """The tax rate printed on each edition's fact page, per $1,000 of assessed value.

    The value is the first `$dd.dd` in the two lines after `TAX RATE`, or failing that the
    line just before it (the 1970 page's OCR set the figure above its label). An edition
    whose fact page yields neither is NOT plotted, and is listed by name -- that is a
    statement about this reader, not about the report (rule 13c)."""
    rows, unread = [], []
    for y in sorted(eds):
        ed = eds[y]
        p, body = fact_page(ed)
        hit = None
        if body:
            lines = body.split('\n')
            for i, ln in enumerate(lines):
                if not re.search(r'TAX RATE', ln, re.I):
                    continue
                window = [ln] + lines[i + 1:i + 3]
                for w in window:
                    m = MONEY.search(w)
                    if m:
                        hit = (w, m)
                        break
                if not hit and i > 0:
                    m = MONEY.search(lines[i - 1])
                    if m and len(lines[i - 1].strip()) < 12:
                        hit = (lines[i - 1], m)
                if hit:
                    break
        if not hit:
            unread.append(y)
            continue
        line, m = hit
        val = float('%s.%s' % (m.group(1), m.group(2)))
        fy = re.search(r'Fiscal (\d{4})', line, re.I) or re.search(r"FY.(\d\d)", body or '')
        rows.append(dict(cite(ed, p), rate=val, printed=' '.join(line.split())))
    return rows, unread


REVALUATIONS = [
    (1970, r'In 1970 Lunenburg went to full and fair valuation\.'),
    (1982, r'STATE MANDATED REVALUATION AND HOW LUNENBURG COMPLIED WITH THE LAW\.'),
    (1989, r'a full 1990 revaluation with subsequent certification by the Department of\s+Revenue\.'),
]


def revaluations(eds):
    return [find(eds, y, pat, 'revaluation %d' % y) for y, pat in REVALUATIONS]


POP_LINE = re.compile(r'^\s*([\d,]{4,6})\s*(\(([^)]*)\))?')


def populations(eds):
    """Every population figure a fact page prints, keyed by the YEAR IT COUNTS, not the
    edition that reprinted it: the 1990 Census figure appears on eleven covers in a row.
    The first edition to print each (year, value) is cited. Where two editions print
    DIFFERENT values for the same census they are both kept and the conflict is listed,
    never averaged."""
    seen = collections.OrderedDict()
    for y in sorted(eds):
        ed = eds[y]
        p, body = fact_page(ed)
        if not body:
            continue
        lines = body.split('\n')
        for i, ln in enumerate(lines):
            if not re.match(r'\s*POPULATION', ln, re.I):
                continue
            head_year = re.search(r'(19\d\d|20\d\d)', ln)
            for nxt in lines[i + 1:i + 3]:
                m = POP_LINE.match(nxt)
                if not m:
                    break
                value = int(m.group(1).replace(',', ''))
                basis = (m.group(3) or '').strip()
                yr = re.search(r'(19\d\d|20\d\d)', basis) or head_year
                if not yr or value < 1000:
                    continue
                ctx = basis + ' ' + ln
                kind = ('preliminary' if re.search(r'prelim', ctx, re.I) else
                        'town census' if re.search(r'town', ctx, re.I) else
                        'state census' if re.search(r'state', ctx, re.I) else
                        'U.S. Census' if re.search(r'U\. ?S\.', ctx) else
                        'kind not printed')
                key = (int(yr.group(1)), value, kind)
                if key not in seen:
                    seen[key] = dict(cite(ed, p), year=key[0], value=value, kind=kind,
                                     printed=' '.join((ln + ' / ' + nxt).split()))
    rows = sorted(seen.values(), key=lambda r: (r['year'], r['edition']))
    # A CONFLICT is two values for one year from the same KIND of count. A town census and
    # the U.S. Census disagreeing in 1990 is two counts, not a conflict; a preliminary
    # count is superseded by the final one, not in conflict with it.
    by_year = collections.defaultdict(list)
    for r in rows:
        if r['kind'] != 'preliminary':
            by_year[(r['year'], r['kind'])].append(r)
    conflicts = {k: v for k, v in by_year.items() if len({r['value'] for r in v}) > 1}
    return rows, conflicts


def charted_population(d):
    """The series the chart draws: every official count the fact pages print -- not the
    town's own annual census, which is a different count, not a preliminary figure, and
    not a year where two editions print two values for the same census."""
    bad = set(d['pop_conflicts'])
    return [r for r in d['pop'] if r['kind'] not in ('town census', 'preliminary')
            and (r['year'], r['kind']) not in bad]


def land_area(eds, year):
    p, body = fact_page(eds[year])
    m = re.search(r'LAND AREA:?\s*\n\s*([\d.]+) square miles', body or '', re.I)
    if not m:
        raise SystemExit('no land area on the %d fact page. Refusing.' % year)
    return dict(cite(eds[year], p), sq_miles=float(m.group(1)))


def roads(eds):
    out = []
    for y in sorted(eds):
        p, body = fact_page(eds[y])
        if not body:
            continue
        m = re.search(r'(TOWN|TOTAL) ROADS:?\s*\n\s*(Approximately\s+)?([\d.]+)\s*miles', body, re.I)
        if m:
            out.append(dict(cite(eds[y], p), miles=float(m.group(3)),
                            printed=' '.join(m.group(0).split())))
    return out


def government(eds):
    out = []
    for y in sorted(eds):
        p, body = fact_page(eds[y])
        if not body:
            continue
        m = re.search(r'TYPE OF GOVERNMENT:?\s*\n\s*([^\n]+)', body, re.I)
        if m and 'town meeting' in m.group(1).lower():
            out.append(dict(cite(eds[y], p), printed=m.group(1).strip()))
    return out


# --------------------------------------------------------------------------------------
# 2. The road to a town manager, quoted from the reports that record each step.
# --------------------------------------------------------------------------------------

def manager_timeline(eds):
    steps = [
        (1966, r'Of the alternative forms of government considered, this Committee believes '
               r'that the\s+"Town Manager with\s+Strong Charter" form',
         'A study committee names a town manager as its preferred form.'),
        (1983, r'investigate the\s+establishment of a Selectmen-Town Manager form of '
               r'(?:\S+\s+)?government',
         'A second study committee is appointed for the same question.'),
        (1999, r'Adoption of the new\s+charter resulted in an increased\s+membership in the '
               r'Board of Selectmen, the Board of Health and the creation of a new\s+'
               r'position, Chief Administrative Financial Officer \(CAFO\)',
         'A Home Rule Charter creates the post, under another name: CAFO.'),
        (2000, r'resulted in the\s+hiring of William J\. Gustus to fill the\s+position',
         'The first CAFO is hired.'),
        (2005, r'The CAFO will be renamed to Town Manager\.',
         'A charter review proposes renaming the post.'),
        (2008, r'these changes to the Charter have not yet received the necessary state '
               r'approvals',
         'The rename is still waiting on the state at the end of the year.'),
        (2009, r'\nTOWN MANAGER\s*\nOne of the most significant events',
         'The report prints its first section headed TOWN MANAGER.'),
    ]
    out = []
    for y, pat, what in steps:
        f = find(eds, y, pat, 'town-manager step %d' % y)
        f['what'] = what
        out.append(f)
    # The same 1966 report's first conclusion, quoted beside the recommendation because
    # the two together are the finding: preferred, and not needed yet.
    out[0]['also'] = find(eds, 1966, r'There is no immediate, pressing need for a major '
                                     r'reorganization of the Lunenburg Town Government',
                          'the 1966 no-pressing-need passage')
    return out


def charter_vote(eds):
    """Question 2 at the May 1999 town election: four precincts and a printed total for
    YES and for NO. The precincts must sum to the printed total or this refuses."""
    ed = eds[1999]
    for p, body in sorted(pages(ed).items()):
        m = re.search(r'QUESTION #2- CHARTER\s*\nYES\s*\n((?:\d+\s*\n){5})NO\s*\n((?:\d+\s*\n){5})',
                      body)
        if not m:
            continue
        yes = [int(x) for x in m.group(1).split()]
        no = [int(x) for x in m.group(2).split()]
        for name, xs in (('YES', yes), ('NO', no)):
            if sum(xs[:4]) != xs[4]:
                raise SystemExit('charter vote %s: precincts %s do not sum to the printed '
                                 'total %d. Refusing.' % (name, xs[:4], xs[4]))
        elec = find(eds, 1999, r'ANNUAL TOWN ELECTION - SATURDAY MAY 1, 1999', 'election')
        return dict(cite(ed, p), yes=yes[4], no=no[4], yes_precincts=yes[:4],
                    no_precincts=no[:4], election=elec)
    raise SystemExit('the 1999 charter question is no longer found. Refusing.')


# --------------------------------------------------------------------------------------
# 3. The school staff rosters: longest runs, the shared name, the first aide.
# --------------------------------------------------------------------------------------

def name_key(n):
    t = [re.sub(r'[^a-z]', '', x) for x in re.split(r'[\s,.]+', n.lower())]
    return ''.join(x for x in t if len(x) > 1 and x not in TITLES)


def rosters(eds):
    with open(ROSTERS, encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < 5000:
        raise SystemExit('staff-roster-entries.csv holds %d rows; refusing to describe '
                         'sixty years of rosters from that.' % len(rows))
    held = sorted({int(r['fy']) for r in rows})
    by = collections.defaultdict(list)
    for r in rows:
        by[name_key(r['name'])].append(r)
    runs = []
    for k, rs in by.items():
        ys = sorted({int(r['fy']) for r in rs})
        cur = [ys[0]]
        chunks = []
        for y in ys[1:]:
            if len([h for h in held if cur[-1] < h < y]) > MAX_ABSENT:
                chunks.append(cur)
                cur = [y]
            else:
                cur.append(y)
        chunks.append(cur)
        for ch in chunks:
            inside = [h for h in held if ch[0] <= h <= ch[-1]]
            ents = sorted((r for r in rs if ch[0] <= int(r['fy']) <= ch[-1]),
                          key=lambda r: (int(r['fy']), int(r['page'] or 0)))
            runs.append(dict(key=k, first=ch[0], last=ch[-1], span=ch[-1] - ch[0],
                             seen=len(ch), held=len(inside), split=len(chunks) > 1,
                             first_entry=ents[0], last_entry=ents[-1]))
    runs.sort(key=lambda r: (-r['span'], -r['seen'], r['key']))
    # naive: one span per name, no breaks -- what a reader matching names alone would say
    naive = sorted(((max(int(r['fy']) for r in rs) - min(int(r['fy']) for r in rs), k)
                    for k, rs in by.items()), reverse=True)

    def entry(e):
        ed = next((x for x in eds.values() if x['filename'] == e['document']), None)
        c = cite(ed, int(e['page'])) if ed else dict(edition=int(e['fy']), page=int(e['page']),
                                                     label=e['fy'], href='')
        return dict(c, name=e['name'], role=' '.join((e['role_raw'] or '').split()),
                    group=' '.join((e['grade_or_dept'] or '').split()))

    top = []
    for r in runs[:6]:
        forms = [e['name'] for e in by[r['key']] if r['first'] <= int(e['fy']) <= r['last']]
        nm = max(forms, key=lambda n: (forms.count(n), len(n)))
        top.append(dict(name=nm, first=r['first'], last=r['last'],
                        span=r['span'], seen=r['seen'], held=r['held'],
                        first_entry=entry(r['first_entry']), last_entry=entry(r['last_entry'])))

    # THE SHARED NAME. The longest naive span whose runs split: one name, two careers.
    shared = None
    for span, k in naive:
        rs = [r for r in runs if r['key'] == k]
        if len(rs) > 1:
            rs.sort(key=lambda r: r['first'])
            a, b = rs[0], rs[-1]
            shared = dict(naive_span=span, name=a['first_entry']['name'],
                          a=dict(first=a['first'], last=a['last'], seen=a['seen'],
                                 first_entry=entry(a['first_entry']),
                                 last_entry=entry(a['last_entry'])),
                          b=dict(first=b['first'], last=b['last'], seen=b['seen'],
                                 first_entry=entry(b['first_entry']),
                                 last_entry=entry(b['last_entry'])))
            break

    # THE FIRST AIDE. The earliest roster entry classified Paraprofessional, and how many
    # the latest edition prints.
    paras = sorted((r for r in rows if r['position'] == 'Paraprofessional'),
                   key=lambda r: (int(r['fy']), int(r['page'] or 0)))
    last_fy = held[-1]
    ranked = collections.Counter(r['position'] for r in rows
                                 if int(r['fy']) == last_fy and r['position']).most_common()
    para = dict(first=entry(paras[0]),
                last_fy=last_fy,
                rank=[p for p, _n in ranked].index('Paraprofessional') + 1,
                ahead=[p for p, _n in ranked][:[p for p, _n in ranked].index('Paraprofessional')],
                last_count=sum(1 for r in rows if r['position'] == 'Paraprofessional'
                               and int(r['fy']) == last_fy))

    names = collections.OrderedDict()
    for y in held:
        names[y] = len({name_key(r['name']) for r in rows if int(r['fy']) == y})
    return dict(held=held, top=top, shared=shared, para=para, names=names,
                entries=len(rows), distinct=len(by))


# --------------------------------------------------------------------------------------
# 4. Then and now: the tables the town printed comparing itself with its past.
# --------------------------------------------------------------------------------------

def csv_rows(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def _row(rows, fy, label_rx, family=None):
    for r in rows:
        if r['fy'] == str(fy) and re.search(label_rx, r['label'], re.I) and \
                (family is None or r['table_family'] == family):
            return r
    raise SystemExit('no %s row /%s/ for %s. Refusing.' % (family or '', label_rx, fy))


def then_and_now(eds):
    val = csv_rows('report-valuation.csv')
    f = 'assessors-1910-1960-comparison'
    t1910 = dict(
        cite(eds[1960], int(_row(val, 1960, r'^Tax rate', f)['page'])),
        rate=(float(_row(val, 1960, r'^Tax rate', f)['v1']),
              float(_row(val, 1960, r'^Tax rate', f)['v2'])),
        houses=(int(float(_row(val, 1960, r'^Dwelling houses', f)['v1'])),
                int(float(_row(val, 1960, r'^Dwelling houses', f)['v2']))),
        camps=int(float(_row(val, 1960, r'^Camps', f)['v1'])),
        trailers=int(float(_row(val, 1960, r'^Trailers', f)['v1'])),
        poll=(int(float(_row(val, 1960, r'poll tax', f)['v1'])),
              int(float(_row(val, 1960, r'poll tax', f)['v2']))),
        real_estate=(float(_row(val, 1960, r'^Value of real estate', f)['v1']),
                     float(_row(val, 1960, r'^Value of real estate', f)['v2'])),
        owners=(int(float(_row(val, 1960, r'^Persons assessed real estate', f)['v1'])),
                int(float(_row(val, 1960, r'^Persons assessed real estate', f)['v2']))),
        motor=float(_row(val, 1960, r'^Excise on motor vehicles', f)['v1']),
        farm=float(_row(val, 1960, r'^Farm animal excise', f)['v1']),
        years=[int(y) for y in _row(val, 1960, r'^Dwelling houses', f)['columns_as_printed'].split(' | ')],
    )
    # THE ONE-VALUE ROWS. Camps, trailers and the two excises print `None` under 1910 and a
    # figure under 1960, and the extract keeps only the figure, in `v1` -- an ordinal, not
    # the 1910 column (CLAUDE.md rule 13). Checked against the printed page: it must say
    # `None` once for each of the four rows, or this reading of v1 is not safe.
    body = pages(eds[1960])[t1910['page']]
    if len(re.findall(r'\bNone\b', body)) < 4 or t1910['years'] != [1910, 1960]:
        raise SystemExit('the 1910-1960 table no longer prints four `None`s under 1910 (or '
                         'its header changed). Refusing to place camps under 1960.')
    t1910['landscape'] = find(eds, 1960, r'"How much will my valuation\s+be increased if I '
                                         r'landscape my\s+lot, or paint my house\?"\s+The '
                                         r'answer is that no increase is ever made for these '
                                         r'reasons\.', 'the Assessors on landscaping')
    tn = csv_rows('report-treasurers-then-and-now.csv')
    pay61 = _row(tn, 1961, r'persons on payroll')
    pay91 = _row(tn, 1991, r'persons on payroll')
    pop61 = _row(tn, 1961, r'^Population')
    pop91 = _row(tn, 1991, r'^Population')
    bp61 = _row(tn, 1961, r'Building applications')
    bp91 = _row(tn, 1991, r'Building Permits')
    # The 1991 table's THEN column is 1961: it must reprint 1961's own figures, or the two
    # tables are not about the same years and cannot be chained.
    for a, b, what in ((pay61['v2'], pay91['v1'], 'payroll'), (pop61['v2'], pop91['v1'], 'population')):
        if float(a) != float(b):
            raise SystemExit('the 1991 THEN column (%s) does not reprint 1961 (%s) for %s. '
                             'Refusing to chain them.' % (b, a, what))
    tn_out = dict(
        c1961=cite(eds[1961], int(pay61['page'])), c1991=cite(eds[1991], int(pay91['page'])),
        payroll=(int(float(pay61['v1'])), int(float(pay61['v2'])), int(float(pay91['v2']))),
        population=(int(float(pop61['v1'])), int(float(pop61['v2'])), int(float(pop91['v2']))),
        permits=(int(float(bp61['v1'])), int(float(bp91['v2']))),
        years=[int(y) for y in pay61['columns_as_printed'].split(' | ')] + [1991],
    )

    lunch = csv_rows('report-school-lunch.csv')
    months = [r for r in lunch if r['fy'] == '1959' and r['table_family'] == 'lunches-served-monthly']
    tot = next(r for r in months if r['label'].upper().startswith('TOTAL'))
    head = tot['columns_as_printed'].split(' | ')[0]
    price = re.search(r'@(\d+)c', head)
    if not price:
        raise SystemExit('the 1959 lunch header no longer names a price. Refusing.')
    msum = sum(int(float(r['v1'])) for r in months if r is not tot and r['v1'])
    lunch_out = dict(cite(eds[1959], int(tot['page'])), total=int(float(tot['v1'])),
                     months_sum=msum, cents=int(price.group(1)), header=head)

    # THE LEVY THEN AND NOW. 1950 is the earliest year any report prints a net amount
    # raised by taxation; FY2010 is the last year the older reports print a levy, read off
    # the same edition's valuation history.
    r50 = next(r for r in val if r['fy'] == '1968' and r['table_family'] == 'raised-by-taxation-five-year'
               and r['v1'] in ('1950.00', '1950'))
    r10 = next(r for r in val if r['fy'] == '2010' and r['table_family'] == 'valuation'
               and r['v1'] in ('2010.00', '2010') and r['v5'])
    levy = dict(y0=1950, v0=float(r50['v2']), c0=cite(eds[1968], int(r50['page'])),
                y1=2010, v1=float(r10['v5']), c1=cite(eds[2010], int(r10['page'])),
                rate0=float(r50['v3']), rate1=float(r10['v2']))
    return dict(t1910=t1910, tn=tn_out, lunch=lunch_out, levy=levy)


# --------------------------------------------------------------------------------------
# 5. Did you know: small things the 1959 report prints, and the lunch-price headers.
#    Each is read from the extracted text and REFUSES if the passage is gone; where the
#    same figure is printed twice in one report, the two must agree.
# --------------------------------------------------------------------------------------

def find_groups(eds, year, pattern, what, page=None):
    """`find`, but also hands back the regex groups, for a passage whose figures we use."""
    ed = eds[year]
    rx = re.compile(pattern, re.I | re.S)
    for p, body in sorted(pages(ed).items()):
        if page is not None and p != page:
            continue
        m = rx.search(body)
        if m:
            return dict(cite(ed, p), quote=' '.join(m.group(0).split())), m.groups()
    raise SystemExit('%s: /%s/ is no longer found in the %d report. Refusing.'
                     % (what, pattern, year))


def tie_1959(eds):
    """The 1959 Selectman race: a tie at the March election, settled by a special election
    in May. The March page prints both candidates' counts; they must be equal, or there was
    no tie to describe."""
    ed = eds[1959]
    march = None
    for p, body in sorted(pages(ed).items()):
        if 'Original Count Before Recount' not in body:
            continue
        h = re.search(r'Howard A\. Hamel\s*\n\s*(\d+)', body)
        t = re.search(r'Eino O\. Toko\s*\n\s*(\d+)', body)
        if h and t:
            march = dict(cite(ed, p), a=int(h.group(1)), b=int(t.group(1)),
                         note='*Original Count Before Recount')
    if not march:
        raise SystemExit('the 1959 Selectman count is no longer found. Refusing.')
    if march['a'] != march['b']:
        raise SystemExit('the 1959 Selectman count reads %d to %d, which is not a tie. '
                         'Refusing to call it one.' % (march['a'], march['b']))
    may, g = find_groups(eds, 1959, r'Special Election\s*\nMay 16, 1959.*?BALLOTS CAST AS '
                                    r'FOLLOWS: Howard A\. Hamel-(\d+); E[il]no O\.\s*Toko-(\d+); '
                                    r'Blanks-(\d+)\.', 'the May 1959 special election')
    reason = find(eds, 1959, r'to fill a vacancy in said office caused by the failure to '
                             r'elect such town\s+officer', 'the special election article')
    board = find(eds, 1959, r'Due to the un-?\s*precedented tie vote for the office of '
                            r'Selectman, the recount, and then a\s+special election to fill '
                            r'the vacancy, your Board was without its full mem-?\s*bership '
                            r'until the middle of May\.', 'the Selectmen on the tie')
    rain = find(eds, 1959, r'Even mother nature conspired against us,\s+bringing one of the '
                           r'rainiest years on record', 'the Selectmen on the rain')
    board['quote'] = board['quote'].replace('un- precedented', 'unprecedented') \
                                   .replace('mem- bership', 'membership')
    return dict(candidates=['Howard A. Hamel', 'Eino O. Toko'], march=march,
                may=dict(may, a=int(g[0]), b=int(g[1]), blanks=int(g[2])),
                reason=reason, board=board, rain=rain)


def clerk_decade(eds):
    """The Town Clerk's ten-year chart of births, marriages and deaths, 1950-1959, in the
    1959 report. Its 1959 column must agree with the list of services on the next page,
    which prints the same three figures again -- two readings of one office's count."""
    years = r'\s*\n'.join(str(y) for y in range(1950, 1959)) + r'\s*\n1959\*'
    col = r'((?:\d+\s*\n){10})'
    c, g = find_groups(eds, 1959, years + r'\s*\nBIRTHS\s*\n' + col + r'MARRIAGES\s*\n' + col
                       + r'DEATHS\s*\n' + col, 'the clerk decade chart')
    births, marriages, deaths = ([int(v) for v in grp.split()] for grp in g)
    _, h = find_groups(eds, 1959, r'Births\s*\n(\d+)\s*\nMarriage Intentions\s*\n\d+\s*\n'
                                  r'Mortgages Recorded\s*\n\d+\s*\nMarriages\s*\n(\d+)\s*\n'
                                  r'Deaths\s*\n(\d+)', 'the 1959 services list')
    if (births[-1], marriages[-1], deaths[-1]) != tuple(int(v) for v in h):
        raise SystemExit('the clerk chart 1959 column %s disagrees with the services list '
                         '%s. Refusing.' % ((births[-1], marriages[-1], deaths[-1]), h))
    asof = find(eds, 1959, r'\* As of February 3, 1960', 'the clerk chart footnote')
    rows = [dict(year=1950 + i, births=births[i], marriages=marriages[i], deaths=deaths[i])
            for i in range(10)]
    return dict(c, rows=rows, asof=asof['quote'].lstrip('* '))


def office_1959(eds):
    lic, g = find_groups(eds, 1959, r'\nDog\s*\n(\d+)\s*\nFish and Game\s*\n(\d+)',
                         'the 1959 licences')
    # The Textract table of the same page must read the same dog count.
    act = [r for r in csv_rows('report-dept-activity.csv')
           if r['fy'] == '1959' and r['label'].strip() == 'Dog']
    if not act or int(float(act[0]['v1'])) != int(g[0]):
        raise SystemExit('the 1959 dog licences: text reads %s, the table %s. Refusing.'
                         % (g[0], act[0]['v1'] if act else 'nothing'))
    prize = find(eds, 1959, r'Last year\'s efforts\s+resulted in a third prize award from '
                            r'the Massachusetts Selectmen\'s Association "In Recognition of\s+'
                            r'the Excellence of Lunenburg\'s Town Report for the Year 1958\."',
                 'the town report prize')
    fact, f = find_groups(eds, 1959, r'Settled:\s*\n(\d{4})\s*\nIncorporated:\s*\n'
                                     r'(August 1, (\d{4}))', 'the 1959 fact page')
    miles, m = find_groups(eds, 1959, r'It is about (\d+) miles from Boston', 'miles to Boston')
    elev, e = find_groups(eds, 1959, r'Elevation at Town Hall:\s*\nApproximately (\d+)\' '
                                     r'above mean sea level', 'elevation')
    jfk = find(eds, 1959, r'Senators\s*\nJOHN F\. KENNEDY, Boston', 'the 1959 senators')
    return dict(licences=dict(lic, dogs=int(g[0]), fish_game=int(g[1])), prize=prize,
                settled=dict(fact, year=int(f[0]), incorporated=f[1], inc_year=int(f[2])),
                boston=dict(miles, miles=int(m[0])), elevation=dict(elev, feet=int(e[0])),
                jfk=dict(jfk, quote='JOHN F. KENNEDY, Boston'))


PRICE = re.compile(r'@\s*(\d\d)\s*[c¢]')


def lunch_prices(eds):
    """What a Type A lunch cost, as the lunch tables' column headers print it. Only a
    header whose price reads cleanly -- digits then `c` or `¢` -- is used; `@254` and
    `@30d` are OCR of a cent sign we will not guess at (rule 13)."""
    out = {'student': [], 'adult': []}
    for r in csv_rows('report-school-lunch.csv'):
        if not r['label'].upper().startswith('TOTAL') or not r['columns_as_printed']:
            continue
        cols = r['columns_as_printed'].split(' | ')
        for who, test in (('student', lambda c: re.search(r'Student|"A" Lunches @', c)
                           and 'Adult' not in c and 'Free' not in c and 'n/c' not in c),
                          ('adult', lambda c: 'Adult' in c and 'Milk' not in c)):
            hit = next((c for c in cols if test(c)), None)
            m = PRICE.search(hit or '')
            if m and int(r['fy']) in eds:
                out[who].append(dict(cite(eds[int(r['fy'])], int(r['page'])),
                                     cents=int(m.group(1)), header=hit))
    for who in out:
        if len(out[who]) < 2:
            raise SystemExit('fewer than two clean %s lunch prices. Refusing.' % who)
        out[who].sort(key=lambda r: r['edition'])
    return out


# --------------------------------------------------------------------------------------
# Everything, once.
# --------------------------------------------------------------------------------------

def gather():
    eds = editions()
    tax, unread = tax_rates(eds)
    pop, conflicts = populations(eds)
    d = dict(eds=eds, tax=tax, tax_unread=unread, reval=revaluations(eds),
             pop=pop, pop_conflicts=conflicts, roads=roads(eds), gov=government(eds),
             manager=manager_timeline(eds), vote=charter_vote(eds), rosters=rosters(eds))
    d.update(then_and_now(eds))
    d.update(tie=tie_1959(eds), clerk=clerk_decade(eds), office=office_1959(eds),
             prices=lunch_prices(eds))
    return d


def derived(d):
    tax = d['tax']
    peak = max(tax, key=lambda r: (r['rate'], -r['edition']))
    last = tax[-1]
    first = tax[0]
    # A CLIFF is a fall of more than a third between consecutive plotted editions.
    cliffs = [(a, b) for a, b in zip(tax, tax[1:]) if b['rate'] < a['rate'] * 2 / 3]
    census = charted_population(d)
    pop_first = census[0]
    pop_last = census[-1]
    area0 = land_area(d['eds'], pop_first['edition'])
    area1 = land_area(d['eds'], pop_last['edition'])
    roads = d['roads']
    gov = d['gov']
    open_from = next((g for g in gov if g['printed'].lower().startswith('open')), None)
    years_to_charter = d['manager'][2]['edition'] - d['manager'][0]['edition']
    return dict(peak=peak, last=last, first=first, cliffs=cliffs, census=census,
                area0=area0, area1=area1,
                pop_first=pop_first, pop_last=pop_last, road_first=roads[0],
                road_last=roads[-1], open_from=open_from, years_to_charter=years_to_charter)


# --------------------------------------------------------------------------------------
# Conclusions.
# --------------------------------------------------------------------------------------

def conclusions_for(d, x):
    rs = d['rosters']
    top = rs['top'][0]
    lv = d['levy']
    mult = lv['v1'] / lv['v0']
    pf, pl = x['pop_first'], x['pop_last']
    rows = [
        conclusion(
            id='the-rate-fell-because-the-town-revalued',
            claim='The tax rate peaked at %s per $1,000 in the %d report; FY2025 prints %s'
                  % (rate(x['peak']['rate']), x['peak']['edition'], rate(x['last']['rate'])),
            so_what='A rate only compares within one assessment, and the reports record %s revaluations.'
                    % C.WORDS[len(d['reval'])] if hasattr(C, 'WORDS') else
                    'A rate only compares within one assessment, and the reports record %s revaluations.'
                    % ['no', 'one', 'two', 'three', 'four', 'five'][len(d['reval'])],
            figures={'peak': figure(x['peak']['rate'], rate(x['peak']['rate']), 'per $1,000'),
                     'py': figure(x['peak']['edition'], str(x['peak']['edition'])),
                     'last': figure(x['last']['rate'], rate(x['last']['rate'])),
                     'n': figure(len(x['cliffs']), C.num(len(x['cliffs'])), 'falls'),
                     'k': figure(1000, '1,000')},
            figure='peak', kind='measured', bearing='sizes',
            detail='The plotted series falls by more than a third from one edition to the '
                   'next %s times, and each fall sits beside a report saying the town '
                   'revalued property that year. A lower rate on higher values is not a '
                   'lower tax bill.' % C.num(len(x['cliffs'])),
            basis='The tax rate on each edition’s fact page, and the three revaluation '
                  'passages quoted below.',
            not_shown='What a household paid in any year. The reports print a rate and a '
                      'town valuation, not a typical bill, before 1976.',
            allow=('FY2025',),
        ),
        conclusion(
            id='the-longest-run-on-the-school-rosters',
            claim='The name %s is printed on school rosters from %d to %d'
                  % (top['name'], top['first'], top['last']),
            so_what='The longest unbroken run of any name across every school roster we hold.',
            figures={'span': figure(top['span'], C.num(top['span']), 'years'),
                     'a': figure(top['first'], str(top['first'])),
                     'b': figure(top['last'], str(top['last'])),
                     'seen': figure(top['seen'], C.num(top['seen'])),
                     'held': figure(top['held'], C.num(top['held']))},
            figure='span', kind='measured', bearing='sizes',
            detail='%s years, printed in %s of the %s roster editions we hold for them. '
                   'A span is first to last appearance, not a hire or a retirement date.'
                   % (C.num(top['span']), C.num(top['seen']), C.num(top['held'])),
            basis='`staff-roster-entries.csv`, names matched with middle initials and '
                  'titles dropped.',
            not_shown='Years outside the reports we hold, and whether a gap year was '
                      'leave or a roster that left the name out.',
        ),
        conclusion(
            id='a-town-manager-took-thirty-three-years',
            claim='A study first recommended a town manager in %d; the charter came in %d'
                  % (d['manager'][0]['edition'], d['manager'][2]['edition']),
            so_what='The post began as the CAFO; the %d report is the first with a Town Manager section.'
                    % d['manager'][-1]['edition'],
            figures={'n': figure(x['years_to_charter'], C.num(x['years_to_charter']), 'years'),
                     'a': figure(d['manager'][0]['edition'], str(d['manager'][0]['edition'])),
                     'b': figure(d['manager'][2]['edition'], str(d['manager'][2]['edition'])),
                     'tm': figure(d['manager'][-1]['edition'], str(d['manager'][-1]['edition'])),
                     'yes': figure(d['vote']['yes'], C.num(d['vote']['yes'])),
                     'no': figure(d['vote']['no'], C.num(d['vote']['no']))},
            figure='n', kind='measured', bearing='sizes',
            detail='%s years. The charter question passed %s to %s at the annual town '
                   'election; two study committees came before it.'
                   % (C.num(x['years_to_charter']), C.num(d['vote']['yes']),
                      C.num(d['vote']['no'])),
            basis='The reports quoted in the timeline, and the printed election return.',
            not_shown='Why it took that long. The reports record the steps, not the '
                      'arguments at the meetings in between.',
        ),
        conclusion(
            id='the-town-nearly-doubled',
            claim='Population went from %s in %d to %s in %d'
                  % (C.num(pf['value']), pf['year'], C.num(pl['value']), pl['year']),
            so_what='Nearly twice the people on the same land: both fact pages print %s square miles.'
                    % ('%g' % x['area1']['sq_miles']),
            figures={'a': figure(pf['value'], C.num(pf['value']), 'residents'),
                     'ay': figure(pf['year'], str(pf['year'])),
                     'b': figure(pl['value'], C.num(pl['value']), 'residents'),
                     'by': figure(pl['year'], str(pl['year'])),
                     'area': figure(x['area1']['sq_miles'], '%g' % x['area1']['sq_miles'])},
            figure='b', kind='measured', bearing='sizes',
            detail='Each figure is the one a report’s fact page prints, by the year it '
                   'counts rather than the edition that reprinted it.',
            basis='The population line on each edition’s fact page.',
            not_shown='Anything after the last census a fact page prints; the FY reports '
                      'stopped printing a population.',
        ),
        conclusion(
            id='the-levy-then-and-now',
            claim='The town raised %s by taxation in %d and levied %s in FY%d'
                  % (usd(lv['v0']), lv['y0'], usd(lv['v1']), lv['y1']),
            so_what='Nominal dollars: the only price index held here starts in 1990, so none is applied.',
            figures={'a': figure(lv['v0'], usd(lv['v0'])), 'ay': figure(lv['y0'], str(lv['y0'])),
                     'b': figure(lv['v1'], usd(lv['v1'])), 'by': figure(lv['y1'], str(lv['y1'])),
                     'x': figure(mult, '%.0f times' % mult), 'ix': figure(1990, '1990')},
            figure='b', kind='measured', bearing='sizes',
            detail='That is %s the 1950 figure, before any allowance for prices, '
                   'population or what the town now does.' % ('%.0f times' % mult),
            basis='The 1968 report’s five-year table (it reprints 1950) and the 2010 '
                  'report’s valuation history.',
            not_shown='The real change. Nothing here deflates a 1950 dollar.',
        ),
        conclusion(
            id='the-first-aide-on-the-rosters',
            claim='The first aide on the rosters is in %d; the %d roster prints %s'
                  % (rs['para']['first']['edition'], rs['para']['last_fy'],
                     C.num(rs['para']['last_count'])),
            so_what='A job the earliest rosters never print is now the %s most printed%s.'
                    % (['', 'single', 'second', 'third', 'fourth', 'fifth'][rs['para']['rank']],
                       (', after ' + ' and '.join(p.lower() + 's' for p in rs['para']['ahead']))
                       if rs['para']['ahead'] else ''),
            figures={'a': figure(rs['para']['first']['edition'], str(rs['para']['first']['edition'])),
                     'b': figure(rs['para']['last_fy'], str(rs['para']['last_fy'])),
                     'n': figure(rs['para']['last_count'], C.num(rs['para']['last_count']),
                                 'paraprofessionals')},
            figure='n', kind='measured', bearing='sizes',
            detail='%s, “%s”. Counted from roster entries classified as paraprofessional.'
                   % (rs['para']['first']['name'], rs['para']['first']['role']),
            basis='`staff-roster-entries.csv`, `position` = Paraprofessional.',
            not_shown='Hours or funding. A roster line is a name, not a full-time post, and '
                      'some years print names with no role to classify.',
        ),
    ]
    t1 = d['t1910']
    homes = t1['houses'][1] + t1['camps']
    rows.append(conclusion(
        id='one-home-in-five-was-a-camp',
        claim='In 1960 the Assessors counted %s camps beside %s dwelling houses'
              % (C.num(t1['camps']), C.num(t1['houses'][1])),
        so_what='A camp is a seasonal house, not lived in year-round; 1910 printed none.',
        figures={'c': figure(t1['camps'], C.num(t1['camps']), 'camps'),
                 'h': figure(t1['houses'][1], C.num(t1['houses'][1]), 'dwelling houses'),
                 'a': figure(1960, '1960'), 'b': figure(1910, '1910'),
                 'homes': figure(homes, C.num(homes), 'homes'),
                 'share': figure(t1['camps'] / homes, '%.0f%%' % (100 * t1['camps'] / homes))},
        figure='c', kind='measured', bearing='sizes',
        detail='%s of the %s homes the table counts. The 1960 report is the only edition we hold '
               'that prints a camp count.' % ('%.0f%%' % (100 * t1['camps'] / homes), C.num(homes)),
        basis='The Assessors’ 1910-1960 comparison table. “Camp” is not defined there; '
              'the gloss is local knowledge (TJ, 30 October 2026).',
        not_shown='Where the camps were, or when they became year-round homes: no later '
                  'report prints the category.',
        allow=('1910-1960',),
    ))
    sh = rs['shared']
    if sh:
        gap = len([h for h in rs['held'] if sh['a']['last'] < h < sh['b']['first']])
        rows.append(conclusion(
            id='one-name-two-careers',
            claim='%s: a school cook from %d to %d, then a name under Phys. Ed. from %d'
                  % (sh['name'], sh['a']['first'], sh['a']['last'], sh['b']['first']),
            so_what='Absent from %s rosters in between; whether it is one person, no report says.'
                    % C.num(gap),
            figures={'a': figure(sh['a']['first'], str(sh['a']['first'])),
                     'b': figure(sh['a']['last'], str(sh['a']['last'])),
                     'c': figure(sh['b']['first'], str(sh['b']['first'])),
                     'g': figure(gap, C.num(gap), 'rosters'),
                     'n': figure(sh['naive_span'], C.num(sh['naive_span']), 'years')},
            figure='n', kind='measured', bearing='sizes',
            detail='Matched on the name alone this would be the longest run on the rosters, '
                   '%s years. A run here breaks on a long absence for exactly this reason.'
                   % C.num(sh['naive_span']),
            basis='`staff-roster-entries.csv`, the entries quoted in the roster section.',
            not_shown='Whether the two careers are one person. Same name is not same person.',
        ))
    tie = d['tie']
    m, y = tie['march'], tie['may']
    rows.append(conclusion(
        id='a-tie-for-selectman',
        claim='In 1959 the race for Selectman tied, %s votes to %s' % (C.num(m['a']), C.num(m['b'])),
        so_what='A special election in May decided it, %s to %s; the board was a member short until then.'
                % (C.num(y['a']), C.num(y['b'])),
        figures={'y': figure(1959, '1959'), 'v': figure(m['a'], C.num(m['a']), 'votes each'),
                 'a': figure(y['a'], C.num(y['a'])), 'b': figure(y['b'], C.num(y['b']))},
        figure='v', kind='measured', bearing='sizes',
        detail='The count the report prints as the original, before the recount. %s won the '
               'May special election over %s.' % (tie['candidates'][0], tie['candidates'][1]),
        basis='The 1959 report: the election return, the special election, and the '
              'Selectmen’s own report.',
        not_shown='What the recount found. The report prints the original count and the '
                  'special election, not the recount’s figures.',
    ))
    cl = d['clerk']['rows']
    lo, hi = cl[0], max(cl, key=lambda r: r['births'])
    if not min(r['births'] for r in cl[1:]) > lo['births']:
        raise SystemExit('the clerk-decade supporting line no longer holds. Refusing.')
    rows.append(conclusion(
        id='the-clerks-decade',
        claim='The Town Clerk recorded %s births in %d and %s in %d'
              % (C.num(lo['births']), lo['year'], C.num(hi['births']), hi['year']),
        so_what='No later year in the clerk’s chart fell back to the %d figure.' % lo['year'],
        figures={'a': figure(lo['births'], C.num(lo['births'])),
                 'ay': figure(lo['year'], str(lo['year'])),
                 'b': figure(hi['births'], C.num(hi['births']), 'births'),
                 'by': figure(hi['year'], str(hi['year'])),
                 'n': figure(len(cl), C.num(len(cl)))},
        figure='b', kind='measured', bearing='sizes',
        detail='From a %s-year chart of births, marriages and deaths the clerk printed in the '
               'last report of the decade: births the office recorded.'
               % C.num(len(cl)),
        basis='The 1959 report, Town Clerk; its last column agrees with the clerk’s '
              'list of services on the next page.',
        not_shown='Why births rose. The chart is a count; it gives no cause.',
    ))
    return emit(ID, rows)


# --------------------------------------------------------------------------------------
# The markdown.
# --------------------------------------------------------------------------------------

def render(d, x):
    rs = d['rosters']
    w = []
    a = w.append
    eds = d['eds']
    a('# %s\n\n' % TITLE)
    a('Sixty-seven annual town reports, %d to FY2025, read into this archive. Every figure '
      'below comes out of them, with the edition and page.\n\n' % min(eds))
    a('![The tax rate printed on the fact page of each annual report, %d to FY2025. It '
      'peaks at %s in the %d report and falls by more than a third %s times, each beside a '
      'report that says the town revalued.](charts/historical-tax-rate.svg)\n\n'
      % (x['first']['edition'], rate(x['peak']['rate']), x['peak']['edition'],
         C.num(len(x['cliffs']))))

    a('## The short version\n\n')
    top = rs['top'][0]
    a('- **The tax rate is not the tax.** %s per $1,000 in the %d report, %s in FY2025, and '
      'each big fall sits beside a report recording a revaluation.\n'
      % (rate(x['peak']['rate']), x['peak']['edition'], rate(x['last']['rate'])))
    a('- **The longest run on the school rosters** is %s, %d to %d.\n'
      % (top['name'], top['first'], top['last']))
    a('- **A town manager took %s years**, from the first study recommending one (%d) to '
      'the charter that created the post (%d).\n'
      % (C.num(x['years_to_charter']), d['manager'][0]['edition'], d['manager'][2]['edition']))
    a('- **Population** went from %s (%d) to %s (%d).\n\n'
      % (C.num(x['pop_first']['value']), x['pop_first']['year'],
         C.num(x['pop_last']['value']), x['pop_last']['year']))

    a('## Across all the years\n\n')
    a('### The tax rate, and the three revaluations\n\n')
    a('The rate each edition prints on its fact page, per $1,000 of assessed value. Until the '
      '1990 edition the page prints a bare rate; from then it names the fiscal year it '
      'applies to, usually the next one. The falls:\n\n')
    a('| from | to | fall |\n|---|---|---:|\n')
    for p, q in x['cliffs']:
        a('| %s, %s | %s, %s | %s |\n' % (link(p), rate(p['rate']), link(q), rate(q['rate']),
                                         C.pct((1 - q['rate'] / p['rate']) * 100, 0)))
    a('\nAnd what the reports say about those years, in their own words:\n\n')
    for r in d['reval']:
        a('- %s: “%s”\n' % (link(r), r['quote']))
    a('\nThe falls and the revaluations line up; what the reports state is the revaluation, '
      'and the rate falling with it is our reading of the coincidence. A rate set on '
      'property valued at a fraction of its worth is not comparable with one set at full '
      'value, so the line above is three or four series, not one.\n\n')
    if d['tax_unread']:
        a('Not plotted: %s. Their fact pages did not yield a rate to this reader, which is a '
          'statement about our extraction, not about the reports.\n\n'
          % ', '.join(str(y) for y in d['tax_unread']))

    a('### How many people\n\n')
    a('![Lunenburg’s population as the fact pages print it, by the year each figure counts, '
      '%d to %d.](charts/historical-population.svg)\n\n'
      % (x['pop_first']['year'], x['pop_last']['year']))
    a('| year counted | population | what kind | first printed in |\n|---:|---:|---|---|\n')
    for r in d['pop']:
        a('| %d | %s | %s | %s |\n' % (r['year'], C.num(r['value']), r['kind'], link(r)))
    if d['pop_conflicts']:
        a('\nWhere two editions print different figures for the same year, both are kept: ')
        a('; '.join('%d, %s (%s)' % (k[0], k[1], ', '.join('%s in %s' % (C.num(r['value']), link(r)) for r in v))
                    for k, v in sorted(d['pop_conflicts'].items())))
        a('. The chart leaves those out rather than choose, and draws only the census counts: '
          'the town’s own yearly census is a different count and is in the table only.\n')
    t = d['tn']
    a('\nThe Treasurer printed a then-and-now table twice, in %s and %s, and the second '
      'reprints the first’s figures as its THEN column, so the two chain: population %s '
      '(1951), %s (1961), %s (1991); persons on the town payroll %s, %s, %s.\n\n'
      % (link(t['c1961']), link(t['c1991']),
         C.num(t['population'][0]), C.num(t['population'][1]), C.num(t['population'][2]),
         C.num(t['payroll'][0]), C.num(t['payroll'][1]), C.num(t['payroll'][2])))
    a('Town roads on the fact page: %s miles in the %d report, %s in the %d report.\n\n'
      % (('%g' % x['road_first']['miles']), x['road_first']['edition'],
         ('%g' % x['road_last']['miles']), x['road_last']['edition']))

    a('### Names on the school rosters\n\n')
    names = rs['names']
    a('![Distinct names printed in the school staff rosters, per annual report, %d to %d.]'
      '(charts/historical-rosters.svg)\n\n' % (rs['held'][0], rs['held'][-1]))
    a('The rosters print %s names in %d and %s in %d. A count of printed names, not a '
      'staffing level: no roster states hours or FTE, some years print only part of the '
      'district, and %s editions have no roster we hold (%s).\n\n'
      % (C.num(names[rs['held'][0]]), rs['held'][0], C.num(names[rs['held'][-1]]),
         rs['held'][-1], C.num(len(set(range(rs['held'][0], rs['held'][-1] + 1)) - set(rs['held']))),
         ', '.join(str(y) for y in sorted(set(range(rs['held'][0], rs['held'][-1] + 1)) - set(rs['held'])))))

    a('## Firsts and longest\n\n')
    a('### The road to a town manager\n\n')
    a('| report | what happened | in the report’s words |\n|---|---|---|\n')
    for s in d['manager']:
        q = '“%s”' % s['quote']
        if s.get('also'):
            q += ' — and, first: “%s”' % s['also']['quote']
        a('| %s | %s | %s |\n' % (link(s), s['what'], q))
    v = d['vote']
    a('\nThe charter was Question 2 on the ballot headed “%s” (%s): YES %s, NO %s, precinct '
      'by precinct %s against %s, and the precincts sum to the printed totals. ' %
      (v['election']['quote'], link(v), C.num(v['yes']), C.num(v['no']),
       ', '.join(C.num(n) for n in v['yes_precincts']),
       ', '.join(C.num(n) for n in v['no_precincts'])))
    if x['open_from']:
        a('The fact page’s *Type of government* line reads “Town Meeting” until the %s, '
          'which first prints “%s”.\n\n' % (link(x['open_from']), x['open_from']['printed']))
    a('### The longest runs on the school rosters\n\n')
    a('A run is the years between the first and last roster a name is printed in, broken '
      'when the name is missing from more than %s consecutive rosters we hold. That '
      'threshold is ours.\n\n' % C.num(MAX_ABSENT))
    a('| name | first | last | span | printed in | first entry | last entry |\n'
      '|---|---|---|---:|---:|---|---|\n')
    for r in rs['top']:
        a('| %s | %d | %d | %s years | %s of %s | %s, “%s” | %s, “%s” |\n'
          % (r['name'], r['first'], r['last'], C.num(r['span']), C.num(r['seen']),
             C.num(r['held']), link(r['first_entry']), r['first_entry']['role'] or r['first_entry']['group'],
             link(r['last_entry']), r['last_entry']['role'] or r['last_entry']['group']))
    sh = rs['shared']
    if sh:
        a('\n**One name, two careers.** Matched on name alone, %s would top that table at '
          '%s years. The rosters print the name from %d (%s, “%s”) to %d (%s, “%s”); it '
          'is then absent from %s rosters in a row, and returns in %d (%s) under “%s”, '
          'last printed in %d. Whether that is one person this archive cannot say, which '
          'is why a run breaks on a long absence.\n\n'
          % (sh['name'], C.num(sh['naive_span']),
             sh['a']['first'], link(sh['a']['first_entry']),
             sh['a']['first_entry']['role'] or sh['a']['first_entry']['group'],
             sh['a']['last'], link(sh['a']['last_entry']),
             sh['a']['last_entry']['role'] or sh['a']['last_entry']['group'],
             C.num(len([h for h in rs['held'] if sh['a']['last'] < h < sh['b']['first']])),
             sh['b']['first'], link(sh['b']['first_entry']),
             sh['b']['first_entry']['role'] or sh['b']['first_entry']['group'],
             sh['b']['last']))
    p = rs['para']
    a('**The first aide.** %s, %s: “%s”. The %d roster prints %s entries classified as '
      'paraprofessional.\n\n' % (p['first']['name'], link(p['first']), p['first']['role'],
                                 p['last_fy'], C.num(p['last_count'])))

    a('## Then and now\n\n')
    t1 = d['t1910']
    a('**1910 against 1960**, a table the Assessors printed in %s: tax rate %s and %s per '
      '$1,000; dwelling houses %s and %s; people assessed a poll tax %s and %s. 1960 also '
      'counts %s camps -- seasonal houses, not lived in year-round -- and %s trailers, which 1910 does not. '
      'Real estate was valued at %s and %s; the motor vehicle excise brought in %s in 1960 '
      'and is printed “None” for 1910. The same page: “%s”\n\n'
      % (link(t1), rate(t1['rate'][0]), rate(t1['rate'][1]), C.num(t1['houses'][0]),
         C.num(t1['houses'][1]), C.num(t1['poll'][0]), C.num(t1['poll'][1]),
         C.num(t1['camps']), C.num(t1['trailers']), usd(t1['real_estate'][0]),
         usd(t1['real_estate'][1]), usd(t1['motor']), t1['landscape']['quote']))
    a('**Building permits**: %s in 1961 and %s in 1991, by the same Treasurer’s tables.\n\n'
      % (C.num(t['permits'][0]), C.num(t['permits'][1])))
    lu = d['lunch']
    a('**School lunch, 1959**: %s Type A lunches at %s cents each over the school year (%s). '
      'The printed total %s the sum of the ten months, %s.\n\n'
      % (C.num(lu['total']), C.num(lu['cents']), link(lu),
         'equals' if lu['total'] == lu['months_sum'] else 'differs from',
         C.num(lu['months_sum'])))
    lv = d['levy']
    a('**The levy**: %s raised by taxation in %d at a rate of %s (%s), and %s levied in '
      'FY%d at %s (%s). Nominal dollars, and two different assessment bases.\n\n'
      % (usd(lv['v0']), lv['y0'], rate(lv['rate0']), link(lv['c0']), usd(lv['v1']),
         lv['y1'], rate(lv['rate1']), link(lv['c1'])))

    a('## Did you know\n\n')
    tie = d['tie']
    a('**The tie of 1959.** The race for Selectman at the March election was printed as %s to '
      '%s, “%s” (%s). A special election on May 16 settled it: %s %s, %s %s, blanks %s (%s). '
      'The Selectmen: “%s” (%s) And: “%s.”\n\n'
      % (C.num(tie['march']['a']), C.num(tie['march']['b']), tie['march']['note'].lstrip('*'),
         link(tie['march']), tie['candidates'][0], C.num(tie['may']['a']), tie['candidates'][1],
         C.num(tie['may']['b']), C.num(tie['may']['blanks']), link(tie['may']),
         tie['board']['quote'], link(tie['board']), tie['rain']['quote']))
    cl = d['clerk']
    a('**The Town Clerk’s decade.** The 1959 report charts births, marriages and deaths '
      'recorded from 1950 (%s; the last column “%s”):\n\n' % (link(cl), cl['asof']))
    a('| year | births | marriages | deaths |\n|---:|---:|---:|---:|\n')
    for r in cl['rows']:
        a('| %d | %s | %s | %s |\n' % (r['year'], C.num(r['births']), C.num(r['marriages']),
                                      C.num(r['deaths'])))
    o = d['office']
    a('\n**The town office in 1959** issued %s dog licences and %s fish and game licences '
      '(%s). And: “%s” (%s)\n\n'
      % (C.num(o['licences']['dogs']), C.num(o['licences']['fish_game']), link(o['licences']),
         o['prize']['quote'], link(o['prize'])))
    a('**The 1959 fact page**: settled %d, incorporated %s, “%s”, and “%s” (%s). Its '
      'list of representatives opens “%s” (%s).\n\n'
      % (o['settled']['year'], o['settled']['incorporated'], o['boston']['quote'],
         o['elevation']['quote'], link(o['settled']), o['jfk']['quote'], link(o['jfk'])))
    pr = d['prices']
    a('**What a school lunch cost**, by the lunch tables’ own column headers: a student '
      'paid %s cents in %d (%s) and %s cents in %d (%s); an adult %s cents, then %s. Only '
      'headers whose cent sign reads cleanly are used.\n\n'
      % (C.num(pr['student'][0]['cents']), pr['student'][0]['edition'], link(pr['student'][0]),
         C.num(pr['student'][-1]['cents']), pr['student'][-1]['edition'], link(pr['student'][-1]),
         C.num(pr['adult'][0]['cents']), C.num(pr['adult'][-1]['cents'])))

    a('## What this does not show\n\n')
    for s in not_established():
        a('- %s\n' % s)
    a('\n## Sources\n\n')
    a('Every annual report is held in this archive with its sha256; the ones quoted here:\n\n')
    for s in sources(d):
        a('- [%s](%s) — `%s`, sha256 `%s…`. Published by the Town of Lunenburg at %s.\n'
          % (s['label'], s['docs_url'], s['filename'], s['sha256'][:12], s['url'] or 'no address recorded'))
    a('\nAnd the extracts: `sources/data/staff-roster-entries.csv` (the rosters), '
      '`report-valuation.csv`, `report-treasurers-then-and-now.csv` and '
      '`report-school-lunch.csv` (Textract tables), and the reports’ extracted text in '
      '`sources/town-annual-reports/text/`. Generated by `scripts/build_historical_report.py`.\n')
    return ''.join(w)


def not_established():
    return [
        'Whether a name on two rosters is one person. The rosters print names, not '
        'employee numbers.',
        'Hire and retirement dates. A run is first and last appearance in the reports we hold.',
        'Any comparison in real dollars. The price index held here starts in 1990.',
        'What a household paid in tax in any year before the reports printed an average bill.',
        'Staffing levels. A roster line is a name, with no hours and no funding source.',
        'The years the archive has no report for, and the pages our reading did not yield.',
    ]


def sources(d):
    cited = set()

    def add(c):
        if c and c.get('edition'):
            cited.add(c['edition'])
    for r in d['tax']:
        add(r)
    for r in d['reval'] + d['pop'] + d['manager']:
        add(r)
    add(d['vote'])
    add(d['t1910'])
    add(d['tn']['c1961'])
    add(d['tn']['c1991'])
    add(d['lunch'])
    add(d['levy']['c0'])
    add(d['levy']['c1'])
    for k in ('board', 'may', 'march'):
        add(d['tie'][k])
    for r in d['prices']['student'] + d['prices']['adult']:
        add(r)
    if d['roads']:
        add(d['roads'][0])
        add(d['roads'][-1])
    for r in d['rosters']['top']:
        add(r['first_entry'])
        add(r['last_entry'])
    out = []
    for y in sorted(cited):
        e = d['eds'][y]
        out.append(dict(label=e['label'], path=e['pdf'], docs_url=e['docs_url'],
                        filename=e['filename'], sha256=e['sha256'], url=e['url'],
                        publisher='Town of Lunenburg',
                        note='The annual town report. Figures are read from its extracted '
                             'text and Textract tables, at the pages cited.'))
    return out


# --------------------------------------------------------------------------------------
# The payload.
# --------------------------------------------------------------------------------------

def payload(d, x):
    rs = d['rosters']
    top = rs['top'][0]
    lv = d['levy']
    census_ok = charted_population(d)
    return dict(
        generated_by='scripts/build_historical_report.py',
        about='What sixty-seven annual town reports say about Lunenburg, %d to FY2025: '
              'the tax rate, the population, the longest names on the school rosters and '
              'the road to a town manager.' % min(d['eds']),
        grain='MIXED, AND EACH FIGURE SAYS WHICH. A tax rate is dollars per $1,000 of '
              'assessed value, as printed; a population is residents in the year the '
              'figure counts; a roster run is years between first and last appearance of '
              'a name. Dollars are nominal.',
        stats=[
            dict(value='%s editions' % C.num(len(d['eds'])),
                 label='annual town reports read, %d to FY2025' % min(d['eds'])),
            dict(value='%s years' % C.num(top['span']),
                 label='the longest run of one name on the school rosters'),
            dict(value=rate(x['peak']['rate']), tone='var(--series-cost)',
                 label='the highest tax rate printed, per $1,000, in the %d report'
                       % x['peak']['edition']),
        ],
        tax_rate=[dict(edition=r['edition'], rate=r['rate'], page=r['page'], label=r['label'],
                       href=r['href'], printed=r['printed']) for r in d['tax']],
        tax_unread=d['tax_unread'],
        revaluations=[dict(edition=r['edition'], page=r['page'], href=r['href'], label=r['label'],
                           quote=r['quote']) for r in d['reval']],
        population=[dict(year=r['year'], value=r['value'], kind=r['kind'], label=r['label'],
                         edition=r['edition'], page=r['page'], href=r['href'])
                    for r in census_ok],
        population_conflicts=[dict(year=k[0], kind=k[1],
                                   printed=[dict(value=r['value'], edition=r['edition'],
                                                 page=r['page'], href=r['href']) for r in v])
                              for k, v in sorted(d['pop_conflicts'].items())],
        population_all=[dict(year=r['year'], value=r['value'], kind=r['kind'],
                             edition=r['edition'], page=r['page'], href=r['href'])
                        for r in d['pop']],
        roster_names=[dict(year=y, names=n) for y, n in rs['names'].items()],
        roster_runs=rs['top'], roster_shared=rs['shared'], first_aide=rs['para'],
        roster_rule='A run breaks when a name is missing from more than %d consecutive '
                    'rosters held.' % MAX_ABSENT,
        town_manager=[dict(edition=s['edition'], page=s['page'], href=s['href'], label=s['label'],
                           what=s['what'], quote=s['quote']) for s in d['manager']],
        charter_vote=dict(yes=d['vote']['yes'], no=d['vote']['no'], page=d['vote']['page'],
                          edition=d['vote']['edition'], label=d['vote']['label'],
                          href=d['vote']['href']),
        then_and_now=dict(t1910=d['t1910'], treasurer=d['tn'], lunch=d['lunch'], levy=lv),
        did_you_know=dict(
            tie=d['tie'], clerk=d['clerk'], office=d['office'],
            prices=dict(student=d['prices']['student'], adult=d['prices']['adult']),
            government=x['open_from'],
            area=x['area1'],
        ),
        sources=sources(d),
        not_established=not_established(),
        conclusions=conclusions_for(d, x),
    )


# --------------------------------------------------------------------------------------
# The SVGs: the markdown's stand-ins for the components (rule 7f's exception).
# --------------------------------------------------------------------------------------

def svg(w, h, body, title, subtitle):
    W, H = w + PAD * 2, h + PAD * 2
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
            'height="%d" role="img" aria-label="%s. %s" font-family=\'%s\'>\n'
            '<rect width="%d" height="%d" fill="%s"/>\n<g transform="translate(%d,%d)">\n'
            '<text x="0" y="15" font-size="13" font-weight="700" fill="%s">%s</text>\n'
            '<text x="0" y="31" font-size="10.5" fill="%s">%s</text>\n%s\n</g>\n</svg>\n'
            % (W, H, W, H, esc(title), esc(subtitle), FONT, W, H, SURFACE, PAD, PAD,
               INK, esc(title), SECOND, esc(subtitle), body))


def _frame(xs, ys, W, H, top=58, left=52, bottom=34, right=24, yfmt=str, ticks=5):
    pw, ph = W - left - right, H - top - bottom
    x0, x1 = min(xs), max(xs)
    # A NICE STEP (1, 2 or 5 times a power of ten), so the gridlines read as $20, $40
    # rather than $29, $59.
    raw = max(ys) * 1.1 / ticks
    mag = 10 ** len(str(int(raw))) / 10 if raw >= 1 else 1
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    ticks = int(-(-max(ys) * 1.05 // step))
    hi = step * ticks

    def X(v):
        return left + pw * (v - x0) / max(x1 - x0, 1)

    def Y(v):
        return top + ph - ph * v / hi
    b = []
    for i in range(ticks + 1):
        v = hi * i / ticks
        b.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s"/>' % (left, Y(v), left + pw, Y(v), GRID))
        b.append('<text x="%d" y="%.1f" font-size="9.5" text-anchor="end" fill="%s">%s</text>'
                 % (left - 6, Y(v) + 3.5, MUTED, yfmt(v)))
    for yr in range((x0 // 10) * 10, x1 + 1, 10):
        if yr >= x0:
            b.append('<text x="%.1f" y="%d" font-size="9.5" text-anchor="middle" fill="%s">%d</text>'
                     % (X(yr), top + ph + 16, MUTED, yr))
    b.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (left, top + ph, left + pw, top + ph, AXIS))
    return X, Y, b


def chart_tax(d, x):
    rows = d['tax']
    W, H = 720, 320
    X, Y, b = _frame([r['edition'] for r in rows], [r['rate'] for r in rows], W, H,
                     yfmt=lambda v: '$%d' % round(v))
    for r in d['reval']:
        b.append('<line x1="%.1f" y1="58" x2="%.1f" y2="286" stroke="%s" stroke-dasharray="4 3"/>'
                 % (X(r['edition']), X(r['edition']), AMBER))
        b.append('<text x="%.1f" y="54" font-size="9.5" text-anchor="middle" fill="%s">revalued</text>'
                 % (X(r['edition']), AMBER))
    pts = ' '.join('%.1f,%.1f' % (X(r['edition']), Y(r['rate'])) for r in rows)
    b.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>' % (pts, BLUE))
    for r in rows:
        b.append('<circle cx="%.1f" cy="%.1f" r="2.6" fill="%s"/>' % (X(r['edition']), Y(r['rate']), BLUE))
    pk = x['peak']
    b.append('<text x="%.1f" y="%.1f" font-size="10.5" font-weight="700" text-anchor="start" fill="%s">%s</text>'
             % (X(pk['edition']) + 6, Y(pk['rate']) + 4, BLUE, rate(pk['rate'])))
    return svg(W, H, ''.join(b), 'The tax rate on the front of each annual report',
               'Dollars per $1,000 of assessed value, as printed, by edition. Dashed lines: '
               'the reports that say the town revalued.')


def chart_pop(d, x):
    rows = charted_population(d)
    W, H = 720, 300
    X, Y, b = _frame([r['year'] for r in rows], [r['value'] for r in rows], W, H,
                     yfmt=lambda v: '{:,}'.format(int(round(v, -2))))
    pts = ' '.join('%.1f,%.1f' % (X(r['year']), Y(r['value'])) for r in rows)
    b.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>' % (pts, BLUE))
    for r in rows:
        b.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (X(r['year']), Y(r['value']), BLUE))
    return svg(W, H, ''.join(b), 'Population, as the reports print it',
               'Residents, by the year each census counted them, as the fact pages print it.')


def chart_rosters(d, x):
    names = d['rosters']['names']
    ys = list(names)
    W, H = 720, 300
    X, Y, b = _frame(ys, list(names.values()), W, H, yfmt=lambda v: str(int(round(v))))
    bw = max(2.0, (W - 76) / (ys[-1] - ys[0] + 1) * 0.7)
    for y, n in names.items():
        b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 % (X(y) - bw / 2, Y(n), bw, Y(0) - Y(n), BLUE))
    return svg(W, H, ''.join(b), 'Names printed in the school staff rosters',
               'Distinct names per annual report. A count of printed names, not of posts '
               'or hours; missing years have no roster held.')


CHARTS = [('historical-tax-rate.svg', chart_tax),
          ('historical-population.svg', chart_pop),
          ('historical-rosters.svg', chart_rosters)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    d = gather()
    x = derived(d)
    files = {OUT: render(d, x),
             PAYLOAD: json.dumps(payload(d, x), indent=1, ensure_ascii=False,
                                 sort_keys=True) + '\n'}
    for name, fn in CHARTS:
        files[os.path.join(CHART_DIR, name)] = fn(d, x)
    if a.check:
        stale = [os.path.basename(p) for p, want in files.items()
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else '') != want]
        if stale:
            print('STALE %s' % ', '.join(sorted(stale)), file=sys.stderr)
            return 1
        print('%s is current' % ID)
        return 0
    for p, want in files.items():
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(want)
    print('wrote %s, %s and %d charts' % (os.path.relpath(OUT, ROOT),
                                          os.path.relpath(PAYLOAD, ROOT), len(CHARTS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
