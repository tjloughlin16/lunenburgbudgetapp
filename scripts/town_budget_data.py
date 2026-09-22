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
# `Protection of persons & property` is what the report's own CONTENTS page calls this
# group; the budget table itself prints the single word `Protection`, and `Total
# Protection`. TJ asked whether `Protection` was the town's word or ours -- it is theirs,
# in the table -- and also that people say `Public Safety`. They do, and the town does not:
# `Public Safety` appears only in narrative, as the Public Safety Building and the Public
# Safety Desk Clerk, never as the name of this budget group. So the longer form the town
# itself prints is used, because bare `Protection` is rule 7b's insider vocabulary and
# `Public Safety` would be a word the document does not use for this thing.
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
    ('protection', 'Protection of persons & property', 'protection'),
    ('health-sanitation', 'Health & Sanitation', 'health'),
    ('public-works', 'Public Works', 'dpw'),
    ('facilities-grounds', 'Facilities & Grounds', 'facilit'),
    ('solid-waste', 'Solid Waste & Recycling', 'solid'),
    ('assistance', 'Assistance', 'assistance'),
    ('schools', 'Schools', 'school'),
    ('library', 'Library', 'librar'),
]
BY_SLUG = {g[0]: g for g in GROUPS}

# WHAT EACH DEPARTMENT IS, in a sentence, so a reader meeting `Maturing Debt & Interest`
# for the first time is not left to infer it from four line items. TJ: *"i need an
# expalanation (from our materials) on what 'Maturing Debt' is"* and *"Maturing debt
# dropping by 600k is interesting but i dont understand it. thats the context."*
#
# EACH ONE IS GROUNDED IN THE LINES THE GROUP ITSELF HOLDS -- they are named in the text,
# so a reader can check the sentence against the table beneath it. Where a sentence goes
# beyond naming the lines it says what KIND of claim it is; none of it is read off a
# document that explains the town's accounting, because the town publishes no such
# document. That absence is itself in money-gaps.csv.
WHAT_IT_IS = {
    'maturing-debt':
        'The town’s annual bill for money it has already borrowed. The group holds '
        '`Principal-Loans` and `Interest-Loans` — repaying the capital on bonds issued to '
        'build things, and the interest on them — plus interest on temporary borrowing, '
        'loan administration fees and bond issuance costs. It buys no service in the year '
        'it is paid: the thing it paid for was built earlier. It falls when bonds finish '
        'and the town has not issued new ones to replace them, which is what has happened '
        'here — almost all of the fall is PRINCIPAL rather than interest.',
    'unclassified':
        'Costs that belong to no single department, printed by the town as `Gen Gov '
        'Unclassified`. Seven tenths of it is `Group Health Insurance` for town and school '
        'employees together; the rest is Medicare, liability and workers’ compensation '
        'insurance, group life, and two reserve funds the town holds against the '
        'unexpected — the `Reserve Fund` and the `Salary Reserve Fund`.',
    'general-government':
        'The town’s own administration: the Select Board, the Town Manager, the Town '
        'Accountant, the Treasurer, the Tax Collector, the Assessors, the Town Clerk, '
        'elections and registration, Information Technology, legal expenses, and the '
        'Planning Board, Zoning Board of Appeals and Conservation Commission.',
    'central-purchasing':
        'One line, for buying things centrally rather than department by department. It is '
        'the smallest group in the budget and the flattest.',
    'protection':
        'Police, Fire, Radio Watch and the inspectors — wiring, plumbing and gas, building, '
        'sealer of weights and measures — plus emergency management and animal control. '
        'The town prints it as `Protection`, and its contents page as `PROTECTION OF '
        'PERSONS & PROPERTY`. Each of Police, Fire, Radio Watch and Other Protection has '
        'its own printed subtotal beneath the group total.',
    'health-sanitation':
        'The Board of Health and the services the town buys in with it — the Nashoba '
        'Associated Boards of Health, nursing, and mental health. Under a fifth of one per '
        'cent of the budget.',
    'public-works':
        'The Highway division and what it runs: labour and overtime, general highway '
        'maintenance, the town garage, traffic signs, snow removal, and vehicle '
        'maintenance for the Highway, Police and Fire fleets. The Park and Cemetery '
        'departments and tree removal sit here too.',
    'facilities-grounds':
        'The buildings the town owns and the grounds around them, including the Park '
        'department’s grounds and utilities for the library. It became a department in '
        'its own right by a recorded vote — Article 7 of the 2022 Annual Town Meeting, '
        'Yes-136 No-28 — which moved town facilities out from under the DPW Director. It '
        'has filed no annual report since, so this is a department the town votes more '
        'than a million dollars a year and publishes nothing else about.',
    'solid-waste':
        'Trash and recycling. The fastest-growing line in the budget by rate, and small '
        'enough that the rate moves the total very little.',
    'assistance':
        'The Council on Aging and Veterans’ services — veterans’ benefits, the veterans’ '
        'agent, the registrar of veterans’ graves and Memorial Day. Each has its own '
        'printed subtotal.',
    'schools':
        'Lunenburg Public Schools and the town’s assessment for Montachusett Regional '
        'Vocational Technical School, plus curriculum updates and school vehicle '
        'maintenance. The largest group in the budget by a long way.',
    'library':
        'One line: the Lunenburg Public Library.',
}

# Proposition 2½ lets the levy rise 2.5% a year before new growth. It is the line every
# one of these rates is measured against, and it is statute rather than an assumption.
LEVY_CAP = 2.5

# The three books whose omnibus reconciles against every total it prints. FY2022 and
# FY2023 land on +$0.80, which is the TOWN's arithmetic and is recorded as an `attested`
# row in table-corrections.csv, not ours.
DETAIL_BOOKS = ('2022', '2023', '2024')


def _norm_label(s):
    """A line's label with the scanner's spacing taken out.

    `Interest -Loans`, `Interest-Loans` and `Interest- Loans` are one line in three years,
    and joined on the raw string they are three lines that each appear once — so the
    biggest single movement in the whole budget, principal and interest falling together,
    showed as a set of lines that appeared and vanished.
    """
    return re.sub(r'\s*-\s*', '-', re.sub(r'\s+', ' ', (s or '').strip()))


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

    PULL is rule 4 and it is the ranking this page uses: a department's share of the budget
    times how far its growth exceeds the levy cap. It is the difference between `the
    schools are the biggest line` (true, and not the finding) and `employee benefits move
    the total more than the schools do` (also true, and the finding).

    BUT IT IS AN INDEX, NOT A DECOMPOSITION, and the page said otherwise for a day. TJ:
    *"'which departments move the total' i dont know what units these are."* He was right
    to ask and the honest answer was worse than a missing label: the twelve pulls sum to
    +1.30 while the budget exceeds the cap by +0.41, because the weight is the END-YEAR
    share and the rate is compound. Calling the unit `points of total growth` claimed an
    additivity that does not hold, which is rule 13's shape -- a derived quantity quoted as
    if it were the thing.

    So `excess` is carried beside it and is what the chart now draws: the department's own
    money times how far its growth exceeds the cap, in DOLLARS A YEAR. Same ranking, a unit
    a resident can check, and it sums to something real -- what the town spends above what
    the levy alone would carry.
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
            pull=(share * (g - LEVY_CAP) / 100) if (g is not None and share) else None,
            excess=(b * (g - LEVY_CAP) / 100) if (g is not None and b) else None))
    rows.sort(key=lambda r: (r['excess'] is None, -(r['excess'] or 0)))
    return rows
