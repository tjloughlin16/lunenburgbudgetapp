#!/usr/bin/env python3
"""The voted town budget, department by department, read out of the annual reports.

One module, because three things need the same figures and must not disagree about them:
the cross-department report, the twelve department reports, and the charts.

THE ONE FACT THAT GOVERNS EVERY READING HERE. **The omnibus budget in an annual report is
the year AHEAD.** The table in the FY2024 book is headed `FY 2025 Omnibus Budget`, and it
is what Town Meeting voted in May 2024 for the fiscal year starting that July. Reading a
book's omnibus as that book's own year puts every figure one year out, and it is the
easiest mistake available here -- the file is called FY2024 and the table is FY2025.

WHAT THE OMNIBUS IS, AND THE THREE THINGS IT IS NOT.

It is what Town Meeting VOTED. That means it is already balanced -- a town cannot vote a
deficit -- so:

  * it is not a request. What each department asked for before the Finance Committee and
    the Town Manager cut it is not in this document, and the difference between the two is
    where a `cut` actually lives.
  * it is not spending. Voted and spent differ, and rule 1 forbids mixing them in one
    calculation.
  * it is not a service level. A department can hold its dollars and cut its hours.

So what this data answers is narrow and worth stating plainly: **who got how much, and how
that changed.** Not who asked, not who spent, not who cut.
"""
import collections
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPROP = os.path.join(ROOT, 'sources', 'data', 'report-appropriations.csv')

# The FY2025 book prints no omnibus table -- Article 10 is prose. Its five funding sources
# are stated and they sum to the total exactly, which is the only check available on it,
# and it passes: 48,942,526.53 + 307,125.25 + 38,453.78 + 31,271.94 + 55,087.50.
FY2026_PROSE = dict(
    fy=2026, total=49374465.00, book=2025, page=140,
    parts=[('raised and appropriated', 48942526.53),
           ('Sewer Enterprise Fund', 307125.25),
           ('Artificial Turf Revolving Fund', 38453.78),
           ('PEG Access and Cable Related Enterprise Fund', 31271.94),
           ('Water Betterment Revenue', 55087.50)])

# The twelve groups the schedule totals, in the town's own printed order, with the name
# this project uses for each.
#
# `Employee benefits & reserves` is printed `Gen Gov Unclassified`, and the rename is not
# cosmetic. `Unclassified` tells a resident nothing -- rule 7b: insider vocabulary is an
# unfinished sentence -- and the first draft of this report guessed at what it meant and
# guessed WRONG, describing it as insurance and retirement. THERE IS NO RETIREMENT LINE IN
# IT, or anywhere else in the omnibus: `county retirement` appears zero times in the whole
# FY2024 report. What is in it, FY2025: Group Health Insurance $3,059,912.01 -- 71.3% of
# the group on its own -- then Medicare at 8.7%, liability, workers' compensation and group
# life at 10.1%, and the Reserve Fund and Salary Reserve Fund at 9.0%. Rule 13's trap in
# miniature: a name was read off a label and a description was derived from the name. A group's PRINTED label is damaged in some years -- FY2023
# prints `Total Gen Gox` and `Total General` where the column ran out -- so matching is on
# a prefix of the squashed label rather than on equality. The prefix for General Government
# is bare `general`, because FY2023 prints `Total General` with the rest of the words lost
# to the column edge -- matching `general gov` dropped that department out of FY2024
# entirely and the table showed an em dash where $2.1M belongs. ORDER MATTERS with a prefix
# that short: `gen go` is tested first and takes `Total Gen Gov Unclassified` with it, so
# `general` cannot reach it. `Subtotal` rows are the nested level (Police, Fire, Radio
# Watch, Other Protection, C.O.A., Veterans) and are NOT groups.
GROUPS = [
    ('maturing-debt', 'Maturing Debt & Interest', 'maturing debt'),
    ('unclassified', 'Employee benefits & reserves', 'gen go'),
    ('general-government', 'General Government', 'general'),
    ('central-purchasing', 'Central Purchasing', 'central'),
    ('protection', 'Protection', 'protection'),
    ('health-sanitation', 'Health & Sanitation', 'health'),
    ('public-works', 'Public Works', 'dpw'),
    ('facilities-grounds', 'Facilities & Grounds', 'facilit'),
    ('solid-waste', 'Solid Waste & Recycling', 'solid'),
    ('assistance', 'Assistance', 'assistance'),
    ('schools', 'Schools', 'school'),
    ('library', 'Library', 'librar'),
]
BY_SLUG = {g[0]: g for g in GROUPS}

# Proposition 2½ lets the levy rise 2.5% a year before new growth. It is the line every
# one of these rates is measured against, and it is statute rather than an assumption.
LEVY_CAP = 2.5

# The three books whose omnibus reconciles against every total it prints. FY2022 and
# FY2023 land on +$0.80, which is the TOWN's arithmetic and is recorded as an `attested`
# row in table-corrections.csv, not ours.
DETAIL_BOOKS = ('2022', '2023', '2024')


def _squash(s):
    return re.sub(r'\s+', ' ', (s or '').strip()).lower()


def _group_of(label):
    t = re.sub(r'^total\s+', '', _squash(label))
    for slug, name, prefix in GROUPS:
        if t.startswith(prefix):
            return slug
    return None


def _rows():
    with open(APPROP, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r.get('table_family') == 'omnibus-budget':
                yield r


def load():
    """Everything the reports need, from one pass."""
    totals, groups, lines, status = {}, collections.defaultdict(dict), \
        collections.defaultdict(lambda: collections.defaultdict(list)), {}
    for r in _rows():
        book = r['fy']
        fy = int(book) + 1          # the omnibus is the year AHEAD
        v = r.get('v1')
        if r['kind'] == 'grand_total' and v:
            totals.setdefault(fy, float(v))
            status[fy] = r['status']
        if r['kind'] == 'subtotal' and v and book in DETAIL_BOOKS:
            g = _group_of(r['label'])
            if g and g not in groups[fy]:
                groups[fy][g] = float(v)
        if r['kind'] == 'row' and book in DETAIL_BOOKS:
            lines[fy][r['page']].append(
                dict(line_no=(r.get('line_no') or '').strip(), label=r['label'].strip(),
                     amount=float(v) if v else None, page=int(r['page'])))
    # THE TWELVE GROUPS MUST COME TO THE PRINTED TOTAL, and the page says so rather than
    # the reader taking it on trust. FY2024 and FY2025 tie to the cent. FY2023 is 30 cents
    # under, and those 30 cents are the TOWN's: it prints `Total Health & Sanitation` at
    # $99,259.60 over five lines that come to $99,259.90, and foots its grand total on the
    # correct figure rather than on the subtotal it printed. Recorded as an attested
    # reading in table-corrections.csv, so this is a difference between two things the
    # document prints, not a doubt about our reading of either.
    reconcile = {}
    for fy, g in groups.items():
        if fy in totals:
            reconcile[fy] = dict(groups=round(sum(g.values()), 2), printed=totals[fy],
                                 difference=round(sum(g.values()) - totals[fy], 2),
                                 n=len(g))
    totals[FY2026_PROSE['fy']] = FY2026_PROSE['total']
    status[FY2026_PROSE['fy']] = 'stated in prose — no department table printed'
    return dict(totals=totals, groups=dict(groups), lines=dict(lines), status=status,
                detail_years=sorted(groups), prose=FY2026_PROSE, reconcile=reconcile)


def department_lines(data, slug):
    """The budget LINES under one group, per year, in printed order.

    Read by walking the page in order and settling at each total, exactly the way the
    extractor reconciles it: the lines belonging to a group are the ones between the
    previous total and this one. That is the document's own structure, and it is why the
    nested `Subtotal Police` rows do not need to be special-cased -- they close their own
    run and the group total that follows closes theirs.
    """
    out = {}
    for fy in data['detail_years']:
        run, found = [], []
        for r in _rows():
            if int(r['fy']) + 1 != fy or r['kind'] == 'footnote':
                continue
            if r['kind'] == 'row':
                run.append(dict(line_no=(r.get('line_no') or '').strip(),
                                label=r['label'].strip(),
                                amount=float(r['v1']) if r.get('v1') else None,
                                page=int(r['page'])))
            elif r['kind'] in ('subtotal', 'grand_total') and r.get('v1'):
                g = _group_of(r['label'])
                if g == slug:
                    found += run
                run = []
        out[fy] = found
    return out


def rate(a, b, years):
    """Compound annual change, as a percentage. None where it cannot be computed."""
    if not a or not b or a <= 0 or years <= 0:
        return None
    return ((b / a) ** (1.0 / years) - 1) * 100


def table(data):
    """One row per department: the three voted years, its rate, its share and its PULL.

    PULL is rule 4 and it is the only ranking this page uses: a department's share of the
    budget times how far its growth exceeds the levy cap, in points of total growth. It is
    the difference between `the schools are the biggest line` (true, and not the finding)
    and `insurance and retirement moves the total more than the schools do` (also true,
    and the finding).
    """
    ys = data['detail_years']
    first, last = ys[0], ys[-1]
    tot = sum(data['groups'][last].values())
    rows = []
    for slug, name, _p in GROUPS:
        a = data['groups'][first].get(slug)
        b = data['groups'][last].get(slug)
        series = {y: data['groups'][y].get(slug) for y in ys}
        g = rate(a, b, last - first)
        share = (b / tot * 100) if (b and tot) else None
        rows.append(dict(
            slug=slug, name=name, series=series, first=a, last=b,
            change=(b - a) if (a and b) else None,
            rate=g, share=share,
            pull=(share * (g - LEVY_CAP) / 100) if (g is not None and share) else None))
    rows.sort(key=lambda r: (r['pull'] is None, -(r['pull'] or 0)))
    return rows
