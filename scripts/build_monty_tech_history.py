#!/usr/bin/env python3
"""MONTY TECH HISTORY: when Lunenburg joined the Montachusett regional vocational district, and what
the Town has paid it in every year the archive holds. One topic page on the Monty Tech shelf; the
hub (build_monty_tech_topics.py) reads its facts and its chart.

    python3 scripts/build_monty_tech_history.py           # write the topic payload
    python3 scripts/build_monty_tech_history.py --check   # fail if it would change

TJ, 31 October 2026: *"do the annual reports explain when monty tech was approved as something we
pay for? If so, put that on the monty tech hub"* and *"including how much we've paid monty tech over
the many years if we have that data"*.

THE JOINING is quoted, never paraphrased into a fact: every quotation below is asserted verbatim
(whitespace aside) against the PDF page of the annual town report's text that it cites, and the
build refuses if one stops matching. What the reports state: a planning committee created by the
1964 Annual Town Meeting (Article 8); a Special Town Meeting on 2 November 1965 that accepted the
Act and agreement establishing the district, 212 to 1; a first appropriation for the district's
expenses at the 5 March 1966 Annual Town Meeting (Article 15). The district was then named the
Northern Worcester County Regional Vocational-Technical School District; the 1967 report says its
formation as the Montachusett district was validated by the Legislature, signed 12 June 1967.

THE SERIES IS ONE BASIS: WHAT THE TOWN ACCOUNTANT RECORDED AS EXPENDED in the year, read off the
accountant's schedule each annual report prints (rule 1: never mixed with a voted figure; the
appropriation is shown beside it in the table, as printed, and never differenced against it). The
FY2026 point is the same quantity from the Town's own MUNIS ledger, period 12. Every year is a row of
`report_appropriations` (the Textract reading of that schedule) named here by edition, page and
label, with the column that holds the expended figure -- except:

  1973      the 1973 report covers an 18-month transition, January 1973 to June 1974, and prints
            only what was expended to 31 December 1973. The 1974 report prints the whole 18 months.
            So the 1973 edition is left out and the 1974 point is labelled as 18 months.
  FY1975    the extractor missed the row (its label is split across two lines on page 77); read
            off the page text, where the figure prints in both money columns.
  FY2011-   read from sources/data/pages-read.csv, where each schedule was read by eye against its
  FY2023    printed header; that reading supersedes the generic extract (which, for one, read FY2011's
            expended cell as `33,124.01`). FY2016, FY2017 and FY2021 have no expended cell there and
            stay on the extract, `check failed`.
  FY2024-   not held: neither report prints an accountant's schedule (the page map classifies every
  FY2025    financial page of both, and the OCR of both was searched for the line). A registered gap.

THE CROSS-CHECK. Monty Tech printed its own table of what it assessed each member town, FY1999 to
FY2018, in the FY2017 annual town report (page 149). For Lunenburg it agrees with the Town's
expended figure to within a dollar in all but two years; the page says which two.

Status is kept, and the chart colours a year by it: whether the reading closed on the schedule's own
printed totals. The generic extract of FY2011-FY2022 does not (`check failed`, as build_monty_tech.py
says of it), which is why the by-eye page reads are preferred where they exist.

RULE 11. This is what the Town's books record as paid to the district, in dollars of each year. It
is not what educating Lunenburg's pupils there costs, and it is not adjusted for inflation.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402

ID = 'monty-tech-history'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
TEXT = os.path.join(ROOT, 'sources', 'town-annual-reports', 'text')
MT = os.path.join(ROOT, 'fy28', 'public', 'data', 'monty-tech.json')
DOCS = '/docs/town-annual-reports/docs/'
SPLIT = 1987          # the signature chart runs FY1987 on (40 points); earlier years are the second chart

REPORTS = {1964: '4507-1964-annual-town-report', 1965: '4508-1965-annual-town-report',
           1966: '4509-1966-annual-town-report', 1967: '4510-1967-annual-town-report',
           1975: '4497-1975-annual-town-report'}

# The joining, quoted. (key, report year, PDF page, the words, verbatim)
QUOTES = [
    ('committee', 1964, 65,
     'VOTED UNANIMOUSLY TO CREATE A SPECIAL UNPAID COMMITTEE TO BE KNOWN AS THE REGIONAL '
     'VOCATIONAL SCHOOL DISTRICT PLANNING COMMITTEE'),
    ('question', 1965, 84,
     'Shall the town accept the provisions of Chapter 568 of the Acts of 1964, as amended by '
     'Chapter 543 of the Acts of 1965, providing for the establishment of a regional school district'),
    ('vote', 1965, 84, 'VOTED. AFFIRMATIVE-212 NEGATIVE-1'),
    ('member', 1965, 94,
     'The Town of Lunenburg, on November 2, 1965, voted to be a member of the Northern-Worcester '
     'County Regional Vocational-Technical School District.'),
    ('first', 1966, 67,
     'VOTED UNANIMOUSLY TO RAISE BY TAXATION AND APPROPRIATE $1,863.98.'),
    ('renamed', 1967, 90,
     'The formation of the Montachusett Regional-Vocational Technical School District was validated '
     'by an act of Legislation and signed by Governor Volpe on June 12, 1967.'),
]
VOTE_FOR, VOTE_AGAINST = 212, 1      # asserted against the 'vote' quotation below

# The expended figure, year by year: (x label, sort key, fiscal year or None, edition, page,
# label as read (LIKE), the column holding EXPENDED). Calendar years until 1972; the 1974 edition
# holds the 18-month transition; fiscal years (July-June) from FY1975.
SCHEDULE = [
    ('1966', 1966, None, '1966', 31, 'Regional Vocational School District Committee', 'v4'),
    ('1967', 1967, None, '1967', 35, 'Montachusett Regional Vocation- Technical School District', 'v4'),
    ('1968', 1968, None, '1968', 43, 'Montachusett Regional Vocational Technical School District', 'v4'),
    ('1969', 1969, None, '1969', 40, 'Montachusett Regional Vocational Technical School District', 'v4'),
    ('1970', 1970, None, '1970', 48, 'Montachusett Regional Vocational Technical School District', 'v4'),
    ('1971', 1971, None, '1971', 59, 'Montachusett Regional Vocational Technical School District', 'v4'),
    ('1972', 1972, None, '1972', 64, 'Montachusett Regional Vocational Technical School District', 'v4'),
    ('1973-FY1974', 1973.5, 1974, '1974', 66, 'Montachusett Regional Vocational Technical School District', 'v4'),
    ('FY1976', 1976, 1976, '1976', 88, 'Montachusett Regional Vocational Technical School District%', 'v4'),
    ('FY1977', 1977, 1977, '1977', 63, 'Montachusett Regional Vocational Technical School District', 'v3'),
    ('FY1978', 1978, 1978, '1978', 62, 'Montachusett Regional Vocational Technical School District', 'v3'),
    ('FY1979', 1979, 1979, '1979', 68, 'Montachusett Regional Vocational Technical School District', 'v4'),
    ('FY1980', 1980, 1980, '1980', 63, 'Montachusett Regional Vocational Technical School District', 'v3'),
    ('FY1981', 1981, 1981, '1981', 117, 'Montachusett Regional Vocational Technical School District', 'v4'),
    ('FY1982', 1982, 1982, '1982', 136, 'Regional Vocational/Technical School Assessment', 'v4'),
    ('FY1983', 1983, 1983, '1983', 62, 'Regional Vocational / Technical School Assessment', 'v3'),
    ('FY1984', 1984, 1984, '1984', 57, 'Regional Vocational Technical School Assessment', 'v2'),
    ('FY1985', 1985, 1985, '1985', 75, 'School Assessment', 'v4'),
    ('FY1986', 1986, 1986, '1986', 57, 'Reg.Vocational Technical School Ass.', 'v4'),
    ('FY1987', 1987, 1987, '1987', 34, '$58329.00 Reg.Voc.Tec.School Assessment', 'v2'),
    ('FY1988', 1988, 1988, '1988', 36, 'Reg. Voc.Tec.School Assessment', 'v3'),
    ('FY1989', 1989, 1989, '1989', 33, '$90161.00 Reg.Voc.Tec.School Assess.', 'v2'),
    ('FY1990', 1990, 1990, '1990', 25, '$113854.00 Reg.Voc.Tec.School Assessment', 'v3'),
    ('FY1991', 1991, 1991, '1991', 28, 'Reg.Voc.Tec.School Assessment', 'v4'),
] + [(C.fy(y), y, y, str(y), p, 'Monty Tech Assessment', 'v3') for y, p in (
    (1992, 27), (1993, 31), (1994, 35), (1995, 55), (1996, 55), (1997, 54), (1998, 51), (1999, 65),
    (2000, 75), (2001, 59), (2002, 53), (2003, 58), (2004, 59), (2005, 59), (2006, 54), (2007, 63),
    (2008, 67), (2009, 52), (2010, 62))] + [
    (C.fy(y), y, y, 'FY%d' % y, p, 'Monty Tech Assessment', 'v3') for y, p in (
        (2016, 29), (2017, 27), (2021, 30))]
# FY2011-FY2023 come first from the PAGE READS (sources/data/pages-read.csv): each schedule read by
# eye against its printed header, which supersedes the generic extract (CLAUDE.md, the annual
# reports). Three years have no read expended cell there and stay on the extract above.
PAGE_READS = os.path.join(ROOT, 'sources', 'data', 'pages-read.csv')
READ_PAGES = {2011: 64, 2012: 64, 2013: 69, 2014: 27, 2015: 27, 2018: 33, 2019: 35, 2020: 29,
              2022: 31, 2023: 31}
# Monty Tech's own table of what it assessed each member town, FY1999-FY2018, printed in the
# FY2017 annual town report (page 149) and read by eye into the same file. A DIFFERENT document
# for the same bill: the cross-check, never part of the series.
DISTRICT_TABLE = (2017, 149, 'Monty Tech assessment, LUNENBURG')
# Two old schedules print no header the extractor could fix; for them the column is named by the
# page's own declared identity (TOTAL FUNDS AVAILABLE = TOTAL EXPENDED + balances), which the
# row's `reconciliation` records.
IDENTITY_NAMED = {'1989': 'v2', '1990': 'v3'}
NOT_HELD = (2024, 2025)
# Whether a figure was checked: the reading's own test that the schedule's columns add up to what
# the page prints (`checked`), or the accounting system's report, which ties to its own grand total.
STATUS_WORDS = {'checked': 'Reconciles on its page', 'check failed': 'Does not reconcile',
                'no check': 'No total to check against', 'read off the page': 'Read off the page'}
RECONCILED = lambda o: o['status'] == 'checked' or o['read'] == 'ledger'
OK_NAME, NOK_NAME = 'Reconciled', 'Not reconciled'


def fail(msg):
    raise SystemExit('build_monty_tech_history: ' + msg)


def norm(s):
    return ' '.join(s.split())


def page_text(year, page):
    path = os.path.join(TEXT, REPORTS[year] + '.txt')
    parts = re.split(r'^===PAGE (\d+)===$', open(path, encoding='utf-8').read(), flags=re.M)
    pages = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
    if page not in pages:
        fail('%s has no page %d' % (REPORTS[year], page))
    return pages[page]


def quotes():
    out = {}
    for key, year, page, words in QUOTES:
        if norm(words) not in norm(page_text(year, page)):
            fail('the %s quotation is no longer on page %d of the %d report: %r' % (key, page, year, words))
        out[key] = dict(year=year, page=page, words=words, href='%s%s.pdf#page=%d' % (DOCS, REPORTS[year], page))
    m = re.search(r'AFFIRMATIVE-(\d+) NEGATIVE-(\d+)', out['vote']['words'])
    if (int(m.group(1)), int(m.group(2))) != (VOTE_FOR, VOTE_AGAINST):
        fail('the vote printed is not %d to %d' % (VOTE_FOR, VOTE_AGAINST))
    return out


def colname(cm, col):
    m = re.search(r'%s=([^|(]+)' % col, cm or '')
    return m.group(1).strip() if m else ''


def series():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    prov = {r['edition']: r for r in db.execute(
        "SELECT * FROM dataset_document WHERE dataset='report-appropriations'")}
    out = []

    def row(edition, page, label):
        rs = db.execute("""SELECT * FROM report_appropriations WHERE edition=? AND page=?
                           AND table_family='accountant-schedule' AND label LIKE ?""",
                        (edition, str(page), label)).fetchall()
        if len(rs) != 1:
            fail('%s p%s %r: %d rows, expected one. A join that matches nothing looks exactly '
                 'like a year the Town paid nothing.' % (edition, page, label, len(rs)))
        return rs[0]

    def doc(edition):
        d = prov.get(edition)
        if not d:
            fail('%s has no row in dataset_document (rule 12)' % edition)
        return d

    for x, key, fy, edition, page, label, col in SCHEDULE:
        r = row(edition, page, label)
        name = colname(r['column_meaning'], col)
        if edition in IDENTITY_NAMED:
            if IDENTITY_NAMED[edition] != col or 'TOTAL EXPENDED' not in (r['reconciliation'] or '') \
                    or ('.%s' % col) not in r['reconciliation']:
                fail('%s: the page identity no longer names %s as TOTAL EXPENDED' % (edition, col))
            name = 'TOTAL EXPENDED (by the page’s own identity)'
        elif 'XPEND' not in name.upper():
            fail('%s p%s: column %s is %r, not an expended column' % (edition, page, col, name))
        if not r[col]:
            fail('%s p%s: no value in %s' % (edition, page, col))
        app = None
        for c in ('v1', 'v2'):
            if 'APPROP' in colname(r['column_meaning'], c).upper():
                app = float(r[c]) if r[c] else None
                break
        d = doc(edition)
        out.append(dict(x=x, key=key, fy=fy, value=float(r[col]), appropriated=app,
                        status=r['status'], column=name, page=page, edition=edition,
                        document=d['document'], href=DOCS + d['document'] + '#page=%d' % page,
                        read='report_appropriations'))

    # 1973: the partial year this series leaves out, asserted so the reason stays true.
    r73 = row('1973', 58, 'Regional Vocational School Assessment')
    if '18 mos. 73-74' not in (r73['column_meaning'] or '') or 'through 12/31/73' not in r73['column_meaning']:
        fail('the 1973 schedule no longer reads as the first half of an 18-month period')
    r74 = [o for o in out if o['edition'] == '1974'][0]
    if float(r73['v1']) != r74['value']:
        fail('the 1973 report’s 18-month funds (%s) are not what the 1974 report says was '
             'expended (%s)' % (r73['v1'], r74['value']))

    # FY1975, off the page: the row the extractor missed.
    t = page_text(1975, 77)
    if 'Montachusett Regional Vocation-' not in t or t.count('131,516.00') < 2:
        fail('the 1975 report page 77 no longer prints the Montachusett line at 131,516.00')
    out.append(dict(x='FY1975', key=1975, fy=1975, value=131516.0, appropriated=None,
                    status='read off the page', column='Expended (both columns print 131,516.00)',
                    page=77, edition='1975', document=REPORTS[1975] + '.pdf',
                    href=DOCS + REPORTS[1975] + '.pdf#page=77', read='page'))

    # FY2011-FY2023, the page reads.
    reads = {}
    for r in csv.DictReader(open(PAGE_READS, encoding='utf-8')):
        y = int(r['fy'])
        if READ_PAGES.get(y) == int(r['page']) and r['fund_name'] == 'Monty Tech Assessment':
            reads.setdefault(y, {}).setdefault(r['column'], set()).add((float(r['value']), r['status']))
    for y, pg in sorted(READ_PAGES.items()):
        cols = reads.get(y)
        if not cols:
            fail('FY%d page %d: no Monty Tech row in pages-read.csv' % (y, pg))
        one = lambda names: [v for n in names for v in cols.get(n, ())]
        exp, app = one(('total_expended', 'expended')), one(('appropriated_forward', 'appropriated'))
        if len({v for v, _ in exp}) != 1 or {st for _, st in exp} != {'checked'}:
            fail('FY%d: the page read does not give one checked expended figure: %r' % (y, exp))
        d = doc('FY%d' % y)
        out.append(dict(x=C.fy(y), key=y, fy=y, value=exp[0][0],
                        appropriated=app[0][0] if len({v for v, _ in app}) == 1 else None,
                        status='checked', column='expended (read by eye)', page=pg, edition='FY%d' % y,
                        document=d['document'], href=DOCS + d['document'] + '#page=%d' % pg,
                        read='pages-read'))
    # FY2011's extract misread the cell as 33,124.01; the page read is the figure. Assert the
    # misread is still the only disagreement, so a change in either surfaces here.
    r = row('FY2011', 64, 'Monty Tech Assessment')
    if round([o for o in out if o['fy'] == 2011][0]['value'] - float(r['v3']), 2) != 600000.0:
        fail('FY2011: the extract and the page read no longer differ by the one misread digit')

    # FY2026, the Town's own ledger: the same quantity, from the accounting system.
    led = json.load(open(MT, encoding='utf-8'))['ledger']
    if led['fy'] != 2026 or led['name'] != 'MONTY TECH':
        fail('monty-tech.json no longer carries the FY2026 MONTY TECH ledger line')
    out.append(dict(x='FY2026', key=2026, fy=2026, value=float(led['expended']),
                    appropriated=float(led['revised']), status='the Town’s ledger, period %s' % led['period'],
                    column='expended (MUNIS)', page=None, edition='FY2026',
                    document=os.path.basename(led['doc_id']), href='/docs/' + led['doc_id'].split('sources/', 1)[1],
                    read='ledger'))
    out.sort(key=lambda o: o['key'])
    if [o['fy'] for o in out if o['fy'] and o['fy'] in NOT_HELD]:
        fail('a year this page calls not held is now held: %s' % NOT_HELD)
    return out


def district():
    """{fy: amount}: Monty Tech's own table of what it assessed Lunenburg (FY2017 report p149)."""
    y, pg, name = DISTRICT_TABLE
    out = {}
    for r in csv.DictReader(open(PAGE_READS, encoding='utf-8')):
        if int(r['fy']) == y and int(r['page']) == pg and r['fund_name'] == name:
            m = re.match(r'y(\d{4})_(\d{4})$', r['column'])
            if not m or r['status'] != 'checked':
                fail('the district table row %r is not a checked fiscal-year column' % r['column'])
            out[int(m.group(2))] = float(r['value'])
    if len(out) < 15:
        fail('the district’s own assessment table holds %d years for Lunenburg' % len(out))
    return out


def page():
    Q = quotes()
    S = series()
    DT = district()
    U = lambda v: figure(v, C.usd(v))
    YR = lambda o: figure(o['key'] if o['fy'] is None else o['fy'], o['x'] if o['fy'] is None else C.fy(o['fy']), 'year')
    by = {o['x']: o for o in S}
    first, last = S[0], S[-1]
    opened = next(o for o in S if o['value'] >= 100000)
    since = [o for o in S if o['fy'] and o['fy'] >= SPLIT]
    early = [o for o in S if not o['fy'] or o['fy'] < SPLIT]
    base = since[0]
    times = last['value'] / base['value']
    # the fall before the long rise: the high of the late 1970s and the low that followed
    # (the 18-month transition is left out of both: it is not a year)
    twelve = [o for o in S if o['edition'] != '1974']
    low = min([o for o in twelve if o['fy'] and 1975 <= o['fy'] <= 1990], key=lambda o: o['value'])
    high = max([o for o in twelve if o['key'] < low['key']], key=lambda o: o['value'])
    y2000 = by['FY2000']
    town = {o['fy']: o['value'] for o in S if o['fy']}
    both = sorted(set(DT) & set(town))
    agree = [y for y in both if abs(town[y] - DT[y]) <= 1]
    differ = [y for y in both if y not in agree]
    if len(both) != len(DT):
        fail('a year in the district’s table has no Town figure: %s' % sorted(set(DT) - set(town)))
    share = (last['value'] - y2000['value']) / (last['value'] - base['value']) * 100

    f = LD.fact
    facts = [
        f('vote', figure(VOTE_FOR, '%d to %d' % (VOTE_FOR, VOTE_AGAINST), 'votes'),
          'Town Meeting vote to join, %s' % 'November 1965', 'published', allow=('1965',)),
        f('first', U(first['value']), 'paid in %s, the first year' % first['x'], 'published',
          label_figures={'y': YR(first)}),
        f('opened', U(opened['value']), 'paid in %s, the first year over %s' % (opened['x'], C.usd(100000)),
          'published', label_figures={'y': YR(opened), 'c': U(100000)}),
        f('agree', figure(len(agree), '%d of %d' % (len(agree), len(both)), 'years'),
          'years the Town’s and Monty Tech’s figures agree', 'published'),
        f('high', U(high['value']), 'paid in %s' % high['x'], 'published', label_figures={'y': YR(high)}),
        f('low', U(low['value']), 'paid in %s' % low['x'], 'published', label_figures={'y': YR(low)}),
        f('base', U(base['value']), 'paid in %s' % base['x'], 'published', label_figures={'y': YR(base)}),
        f('last', U(last['value']), 'paid in %s, the Town’s ledger' % last['x'], 'published',
          label_figures={'y': YR(last)}),
        f('gap', None, 'paid in %s and %s' % (C.fy(NOT_HELD[0]), C.fy(NOT_HELD[-1])), 'gap',
          label_figures={'a': figure(NOT_HELD[0], C.fy(NOT_HELD[0]), 'year'),
                         'b': figure(NOT_HELD[-1], C.fy(NOT_HELD[-1]), 'year')},
          closes='The Town Accountant’s year-end expenditure report, general fund line 310, '
                 'for those two years'),
    ]
    times_f = figure(round(times, 1), '%.1f' % times, 'times')
    share_f = figure(round(share), '%d%%' % round(share), '%')
    con = TP.conclusion
    conclusions = [
        con('Town Meeting voted %d to %d on November 2, 1965, to join the regional district.'
            % (VOTE_FOR, VOTE_AGAINST), ['vote'],
            {'v': figure(VOTE_FOR, '%d to %d' % (VOTE_FOR, VOTE_AGAINST), 'votes')},
            allow=('November 2, 1965',),
            so='Membership was a Town Meeting decision; the bill is its own line in the Town’s '
               'budget, beside the school department’s.'),
        con('In %s of %s years from %s, the Town’s figure is within a dollar of Monty Tech’s own.'
            % (len(agree), len(both), C.fy(min(both))), ['agree'],
            {'n': figure(len(agree), str(len(agree)), 'years'), 'm': figure(len(both), str(len(both)), 'years'),
             'y': figure(min(both), C.fy(min(both)), 'year')},
            so='Two documents, the Town’s and the district’s, agree on the bill; %s differ, and '
               'neither says why.' % ' and '.join(C.fy(y) for y in differ),
            so_figures={'d%d' % i: figure(y, C.fy(y), 'year') for i, y in enumerate(differ)}),
        con('It peaked at %s in %s and fell to %s by %s before the long rise.'
            % (C.usd(high['value']), high['x'], C.usd(low['value']), low['x']),
            ['high', 'low', 'base', 'last'],
            {'a': U(high['value']), 'y': YR(high), 'b': U(low['value']), 'z': YR(low)},
            so='Nothing in these reports says why it fell. Enrolment and state aid are candidates; '
               'nothing here tests either.'),
        con('Since %s the payment grew %s times; %s of that rise came after %s.'
            % (base['x'], '%.1f' % times, '%d%%' % round(share), y2000['x']),
            ['base', 'last'], {'y': YR(base), 't': times_f, 's': share_f, 'z': YR(y2000)},
            so='Dollars of each year, not adjusted for inflation, and what the Town is billed, not '
               'what the school costs.'),
    ]

    def track_split(rows):
        ok = [o['value'] if RECONCILED(o) else None for o in rows]
        nok = [o['value'] if not RECONCILED(o) else None for o in rows]
        return [TP.track(n, v) for n, v in ((OK_NAME, ok), (NOK_NAME, nok)) if any(v)]

    xs = [o['x'] for o in since]
    for y in NOT_HELD:                       # a gap is drawn as a gap, in its place
        xs.insert(xs.index(C.fy(last['fy'])), C.fy(y))
    rows_since = [by.get(x) for x in xs]
    vals = lambda pick: [pick(o) if o else None for o in rows_since]
    chart = TP.series('What Lunenburg paid Monty Tech', xs, [
        TP.track(OK_NAME, vals(lambda o: o['value'] if RECONCILED(o) else None)),
        TP.track(NOK_NAME, vals(lambda o: o['value'] if not RECONCILED(o) else None)),
    ], '$', kind='bar', stacked=True,
        note='Expended, as each year’s annual town report prints it; FY2026 from the Town’s ledger. '
             'No figure is held for FY2024 or FY2025.', note_allow=('FY2026', 'FY2024', 'FY2025'))
    also = TP.series('The early years', [o['x'] for o in early], track_split(early), '$',
                     kind='bar', stacked=True,
                     note='Calendar years to 1972; the 1974 report covers January 1973 to June 1974, '
                          'eighteen months; fiscal years after.',
                     note_allow=('1972', '1974', '1973'))

    def table_rows(rows):
        out = []
        for o in reversed(rows):
            out.append(dict(label=o['x'], cells=[
                C.usd(o['value']), C.usd(o['appropriated']) if o['appropriated'] else '—',
                C.usd(DT[o['fy']]) if o['fy'] in DT else '—',
                ('%s, p%d' % (o['edition'], o['page'])) if o['page'] else o['document'],
                STATUS_WORDS.get(o['status'], o['status'])]))
        return out
    cols = ['Expended', 'Appropriated, as printed', 'Monty Tech’s own figure', 'Report, page', 'Status']
    mid = [o for o in since if o['fy'] < 2007]
    late = [o for o in since if o['fy'] >= 2007]
    K = ['ledger', 'stated', 'stated', 'stated', 'stated']
    table = dict(caption='Every year held', views=[
        dict(key='late', label='%s on' % late[0]['x'], columns=cols, kinds=K, rows=table_rows(late),
             note='Status is the reading’s own check: whether the schedule’s columns add to the totals '
                  'it prints. The FY2011 expended cell is repaired from its own printed balance.'),
        dict(key='mid', label='%s to %s' % (mid[0]['x'], mid[-1]['x']), columns=cols, kinds=K,
             rows=table_rows(mid),
             note='Appropriated is the column the schedule prints, which some years call '
                  'Appropriated Forward: the vote plus any balance carried in.'),
        dict(key='early', label='To %s' % early[-1]['x'], columns=cols, kinds=K, rows=table_rows(early),
             note='Calendar years to 1972; the 1974 report’s schedule covers January 1973 to June 1974.'),
    ])

    joined = TB.explain('How Lunenburg joined', [
        ('**1964.** The Annual Town Meeting created a three-member Regional Vocational School '
         'District Planning Committee (Article 8).', None, ('1964', '8')),
        ('**November 2, 1965.** A Special Town Meeting was asked: *“%s”* The record: *“%s”*'
         % (Q['question']['words'], Q['vote']['words']), None,
         ('November 2, 1965', 'Chapter 568 of the Acts of 1964', 'Chapter 543 of the Acts of 1965',
          'AFFIRMATIVE-212 NEGATIVE-1')),
        ('**March 5, 1966.** The first appropriation for the district’s expenses, Article 15: '
         '*“%s”*' % Q['first']['words'], None, ('March 5, 1966', '15', '$1,863.98')),
        ('It was first named the Northern Worcester County Regional Vocational-Technical School '
         'District. The 1967 report: *“%s”*' % Q['renamed']['words'], None, ('1967', 'June 12, 1967')),
    ], place='body', tone='plain')

    sources = [
        dict(key='r1964', label='1964 Annual Town Report, Article 8, PDF page 65 — 4507-1964-annual-town-report.pdf',
             href=Q['committee']['href']),
        dict(key='r1965', label='1965 Annual Town Report, Special Town Meeting of 2 November 1965, PDF page 84 — '
                                '4508-1965-annual-town-report.pdf', href=Q['vote']['href']),
        dict(key='r1965b', label='1965 Annual Town Report, Regional Vocational School District Committee, PDF '
                                 'page 94 — 4508-1965-annual-town-report.pdf', href=Q['member']['href']),
        dict(key='r1966', label='1966 Annual Town Report, Article 15, PDF page 67 — 4509-1966-annual-town-report.pdf',
             href=Q['first']['href']),
        dict(key='r1967', label='1967 Annual Town Report, the district committee’s report, PDF page 90 — '
                                '4510-1967-annual-town-report.pdf', href=Q['renamed']['href']),
        dict(key='approps', label='Lunenburg Budget Project — report-appropriations.csv: the accountant’s '
                                  'schedule of every annual town report, row by row, with its page',
             href='/docs/data/report-appropriations.csv'),
        dict(key='reads', label='Lunenburg Budget Project — pages-read.csv: the FY2011-FY2023 schedules and '
                                'Monty Tech’s table, read by eye against each printed header',
             href='/docs/data/pages-read.csv'),
        dict(key='r2017', label='FY2017 Annual Town Report, Monty Tech’s assessments by member town, PDF '
                                'page 149 — 4124-fy-2017-annual-town-report.pdf',
             href=DOCS + '4124-fy-2017-annual-town-report.pdf#page=149'),
        dict(key='r1975', label='1975 Annual Town Report, accountant’s schedule, PDF page 77 — '
                                '4497-1975-annual-town-report.pdf', href=by['FY1975']['href']),
        dict(key='ledger', label='Town of Lunenburg — MUNIS year-to-date expense report, general fund, '
                                 'FY2026 period 12 — %s' % last['document'], href=last['href']),
        dict(key='reports', label='Town of Lunenburg — the annual town reports, catalogued with their addresses — index.csv',
             href='/docs/town-annual-reports/index.csv'),
    ]
    joins = ('r1964', 'r1965', 'r1965b', 'r1966', 'r1967')
    cite = TP.cite
    return TP.page(
        ID,
        'Lunenburg voted %d to %d in 1965 to join Monty Tech; it paid %s in %s and %s in %s.'
        % (VOTE_FOR, VOTE_AGAINST, C.usd(first['value']), first['x'], C.usd(last['value']), last['x']),
        facts, conclusions, chart=chart, also=[also], table=table, sources=sources,
        finding_figures={'v': figure(VOTE_FOR, '%d to %d' % (VOTE_FOR, VOTE_AGAINST), 'votes'),
                         'a': U(first['value']), 'y': YR(first), 'b': U(last['value']), 'z': YR(last)},
        finding_allow=('1965',),
        flow=['finding', cite(('chart', 0), 'approps', 'reads', 'ledger', 'reports'), cite(joined, *joins),
              cite('ladder', 'r1965', 'approps', 'reads', 'r2017', 'ledger'),
              cite(('chart', 1), 'approps', 'r1975'), 'related',
              cite(('table', 0), 'approps', 'reads', 'r2017', 'r1975', 'ledger', 'reports'), 'sources'])


def render():
    return json.dumps(page(), indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('monty tech history: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
