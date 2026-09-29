#!/usr/bin/env python3
"""What this project has READ but cannot yet TRUST, registered as gaps.

    python3 scripts/build_extraction_gaps.py           # merge `extraction` rows into money-gaps.csv
    python3 scripts/build_extraction_gaps.py --check   # fail if they have drifted

TJ, 20 September 2026, on discovering that stabilization fund history was unusable only
because he asked for it: "we need to surface these gaps so I dont find them with
questions like this."

THE GAP THIS CLOSES IS ABOUT US, NOT THE TOWN. Every other side in money-gaps.csv records
something the town does not publish. This one records something the town DID publish,
that we read, and that nothing has yet reconciled -- 13,405 rows off sixteen annual
reports, of which 409 are checked. The rows are in the database and served by the API, so
a reader or an agent can query them and get a confident-looking answer off a table that is
54% check-failed.

`status` is what stands between that and a wrong number, and CLAUDE.md says nothing may be
aggregated without splitting on it. That rule works and it is invisible: it lives in a
reference note, while the data itself is one query away on a public endpoint. So the
shortfall belongs where every other limit of this archive is published.

WHY GENERATED. The counts move every time an extractor improves, and a hand-typed "3.1%
checked" would be wrong the first time somebody fixed a ruler -- rule 2, on a figure that
is exactly the kind this project keeps getting caught by.

WHY IT MERGES RATHER THAN REWRITES. money-gaps.csv has several authors and was clobbered
twice in one day. This replaces only the rows whose side is `extraction` and leaves every
other row exactly as found, byte for byte, including the file's newline convention.
"""
import argparse
import csv
import io
import os
import collections
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, 'sources', 'data', 'extraction-plan.csv')
PAGES = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
SIDE = 'extraction'

# Only families where the shortfall actually costs a reader an answer. A dataset of names
# and dates does not need a reconciliation to be useful; one carrying DOLLARS does, and
# those are the ones somebody will try to trend.
PLAN_DATASET = {
    'report_trust_funds': 'trust_funds',
    'report_appropriations': 'appropriations',
    'report_capital_projects': 'capital_projects',
    'report_debt': 'debt',
    'report_gross_wages': 'gross_wages',
}

WORTH_SAYING = {
    'report_trust_funds': ('the stabilization and trust fund balances',
                           'how much the town holds in reserve, and how that has moved'),
    'report_appropriations': ('what Town Meeting appropriated, article by article',
                              'what the town voted to spend, year over year'),
    'report_capital_projects': ('the capital projects and what they cost',
                                'what the town has built and what it paid'),
    'report_debt': ('the debt schedule',
                    'what the town owes and when it falls due'),
    'report_gross_wages': ('gross wages, name by name',
                           'what the town pays its people in total'),
}


# ------------------------------------------- A PAGE READ AND REFUSED IS A GAP, NOT A QUEUE
#
# The two kinds of shortfall here are not the same thing and were only registered as one.
# A row that failed its reconciliation IS PUBLISHED and looks confident -- that is what
# everything above this line is about. A page an extractor READ AND REFUSED publishes
# NOTHING: its rows were never written, or were deleted for not summing to the total the
# page itself prints, so a query about that year returns silence and the silence reads as
# though the town never printed it.
#
# Rule 7c: a conclusion we cannot draw is a GAP and it gets registered, not merely written
# in the prose of whichever page hit it. Ten receivables pages sat in a queue counter for
# four days as work nobody had started.
#
# GENERATED, for rule 2's reason. These counts fall as each extractor is fixed, and a
# hand-typed "ten pages" would be wrong the first time one was -- which is the exact
# failure the state machine in map_annual_report_pages.py was rewritten to stop.
#
# ONE ROW PER REFUSING EXTRACTOR, because the remedy is per extractor. The question is
# phrased as what a READER cannot answer, never as a complaint about our code, and a family
# missing from this table FAILS the build rather than going unregistered.
REFUSED_FAMILY = {
    'debt-repayment-detail-refused': (
        'What did the town owe on each bond issue, principal and interest, in the years '
        'whose repayment schedule cannot be read?',
        'the debt repayment schedule',
        'a reader of `scripts/extract_debt_tables.py` measuring the year header and '
        'splitting the merged year boxes by the pitch the page itself sets, then '
        'publishing only the columns where PRINCIPAL + INTEREST foots to the printed '
        'TOTAL for that issue'),
    'receivables-refused': (
        'What was the town owed, account by account, in the years whose receivables page '
        'will not foot?',
        'what is owed to the town',
        '`scripts/extract_receivables.py` made to sum to the totals those pages print; '
        'the pages are legible and they grade the extractor'),
    'gross-wages-refused': (
        'What did the town pay its people, name by name, in the years whose payroll '
        'listing produced nothing?',
        'gross wages, name by name',
        'a Vision RE-READ of the page, which is free and is what closed FY2019: its '
        'seven pages held 871 boxes in our cache against 1,753 on a re-read, and two of '
        'them held the surname column and no money at all. The refusals that survive a '
        're-read are scan defects rather than layout \u2014 FY2019 p200 loses a 21-row '
        'band that produced no box at scale 2, 3, 4, 5, 6 or 8 \u2014 and those close '
        'only with a better copy of the page from the Town. Note that the town stopped '
        'printing the department beside each name after FY2016, so these pages bound the '
        'question rather than settling it'),
    'appropriations-supplement-refused': (
        'What was appropriated on the supplementary pages that do not foot to their own '
        'subtotals?',
        'what Town Meeting appropriated',
        'the subtotal identity those pages state about themselves, applied per column'),
    'extraction-blocked': (
        'What cash did the Treasurer hold in the years whose column does not foot to the '
        'page\u2019s own printed total?',
        'the Treasurer\u2019s cash on hand',
        'the column ruler in the treasurer\u2019s-cash reader; the page prints the total '
        'the column must reach, and `sources/data/extraction-blocked.csv` records both '
        'figures'),
    'read-and-refused': (
        'What is on the pages a model read and returned no rows for?',
        'pages with no extractor of their own',
        'reading the refusal note in `sources/data/annual-report-reads/` and deciding '
        'whether the page holds a table at all \u2014 some of them correctly do not'),
}


def refused_pages():
    """{register: [fy]} for pages in state `refused`, off the generated page map.

    THE MAP IS THE SOURCE and not the refusal files, because a page one extractor refused
    and another read is READ: nothing is missing and there is no gap. `state == 'refused'`
    is the join already made -- refused by somebody and cited by nobody.
    """
    out = collections.defaultdict(list)
    if not os.path.exists(PAGES):
        return out
    for r in csv.DictReader(open(PAGES, encoding='utf-8')):
        if (r.get('state') or '') != 'refused':
            continue
        for who in (r.get('refused_by') or '').split(','):
            who = who.strip()
            if who:
                out[who].append(int(r['fy']))
    return out


def refusal_gap_rows():
    rows = []
    found = refused_pages()
    unknown = sorted(set(found) - set(REFUSED_FAMILY))
    if unknown:
        raise SystemExit(
            'UNDECLARED: %s refused pages and is not in REFUSED_FAMILY in %s. Add the '
            'question a reader cannot answer and the document or fix that would close it.'
            % (', '.join(unknown), os.path.basename(__file__)))
    for who, (what, subject, closes) in sorted(REFUSED_FAMILY.items()):
        yrs = sorted(set(found.get(who, ())))
        if not yrs:
            continue
        pages = len(found[who])
        rows.append({
            'side': SIDE,
            'what': what,
            'why': ('%d page%s of %s in the annual town reports %s READ AND REFUSED: an '
                    'extractor reached %s, could not tie the rows to a total the page '
                    'itself prints, and published nothing. So a query about %s returns '
                    'silence for %s, and the silence is ours rather than the town’s '
                    '— every one of these pages IS printed. Refusals and their '
                    'reasons are in `sources/data/%s.csv`; the pages are listed in '
                    '`sources/data/annual-report-pages.csv` where `state` is `refused`. '
                    'Re-running a model over them returns the same refusal and pays for '
                    'it. — closes: %s.'
                    % (pages, '' if pages == 1 else 's', subject,
                       'is' if pages == 1 else 'are',
                       'them' if pages > 1 else 'it', subject,
                       # THE YEARS THEMSELVES, NOT A RANGE. `FY2013–FY2023` claims
                       # eleven years of silence where there are seven, and a resident
                       # reading the gaps page has no way to tell which. A range is only
                       # honest when it is contiguous.
                       ', '.join('FY%d' % y for y in yrs)
                       if yrs[-1] - yrs[0] + 1 != len(yrs) or len(yrs) < 3
                       else 'FY%d–FY%d' % (yrs[0], yrs[-1]),
                       who, closes)),
        })
    return rows


def counts():
    db = sqlite3.connect(DB)
    out = {}
    for table, (what, why) in WORTH_SAYING.items():
        try:
            rows = dict(db.execute(
                'SELECT status, COUNT(*) FROM %s GROUP BY status' % table).fetchall())
        except sqlite3.OperationalError:
            continue
        total = sum(rows.values())
        if not total:
            continue
        out[table] = dict(what=what, why=why, total=total,
                          checked=rows.get('checked', 0),
                          failed=rows.get('check failed', 0),
                          nocheck=rows.get('no check', 0))
    return out


def difficulty(table):
    """What the per-year survey in extraction-plan.csv says about this family.

    THE SURVEY IS THE POINT. A reader told only that 54% of rows failed will assume
    neglect. The plan says otherwise: somebody opened every page and wrote down what was
    wrong with it -- mirrored layouts, a missing fund-name column, two years with
    different column counts. Ten of seventeen trust-fund years need real PDF geometry
    rather than text, which is a different and larger job than fixing a ruler, and saying
    so is the difference between a backlog and an accusation.
    """
    name = PLAN_DATASET.get(table)
    if not name or not os.path.exists(PLAN):
        return None
    rows = [r for r in csv.DictReader(open(PLAN, encoding='utf-8'))
            if r.get('dataset') == name]
    if not rows:
        return None
    c = collections.Counter((r.get('extractable') or '?').strip() for r in rows)
    return dict(years=len(rows), counts=c,
                checkable=sum(1 for r in rows if (r.get('checkable') or '').strip() == 'yes'))


def gap_rows():
    rows = refusal_gap_rows()
    for table, c in sorted(counts().items()):
        if c['checked'] == c['total']:
            continue
        pct = c['checked'] / c['total'] * 100
        rows.append({
            'side': SIDE,
            'what': 'Can we trust %s enough to chart %s?' % (c['what'], c['why']),
            'why': why_for(table, c),
        })
    return rows


def why_for(table, c):
    base = ('%s of %s rows in `%s` are reconciled to a total the document itself prints — '
            '%s failed that check and %s were never checked. The figures are read and '
            'published, so a query returns them and they look confident; only the '
            '`status` column says otherwise.'
            % ('{:,}'.format(c['checked']), '{:,}'.format(c['total']), table,
               '{:,}'.format(c['failed']), '{:,}'.format(c['nocheck'])))
    d = difficulty(table)
    if d:
        hard = d['counts'].get('not without geometry', 0)
        messy = d['counts'].get('messy', 0)
        clean = d['counts'].get('clean', 0)
        base += (' Every page was surveyed before anyone tried: of %d years, %d need real '
                 'PDF geometry rather than text, %d are messy and %d are clean — mirrored '
                 'layouts, rows offset from their own names, a missing fund-name column, '
                 'and column counts that change between years.'
                 % (d['years'], hard, messy, clean))
        # THE ANCHOR CLAUSE IS CONDITIONAL AND USED NOT TO BE. It read `%d of %d years do
        # print a grand total to reconcile against, so the anchor exists` whatever the
        # count was, so the gross wages row said `0 of 16 ... so the anchor exists` and
        # then promised a remedy `tied to the printed total on each page`. A wage page
        # prints no total -- checked box by box on all seven of FY2019's -- so the row was
        # naming a document that does not exist as the thing that would settle it. Rule
        # 7c: a gap with no named remedy is a grievance, and a gap with an IMPOSSIBLE one
        # is worse, because it reads as a records request somebody could make.
        if d['checkable']:
            base += (' %d of %d years do print a grand total to reconcile against, so the '
                     'anchor exists.' % (d['checkable'], d['years']))
            return base + (' — closes: a geometry-aware extractor for this table family, '
                           'tied to the printed total on each page. The per-year survey '
                           'is in `sources/data/extraction-plan.csv`.')
        base += (' NO year of this family prints a grand total, so there is no arithmetic '
                 'on the page to foot a row against and no extractor can supply one.')
        return base + (' — closes: nothing we can build. What stands in for a total here '
                       'is the PAIRING and the order the list prints itself in, both of '
                       'which prove the assignment and say nothing about the digits; a '
                       'reconcilable figure needs a total from the Town. The per-year '
                       'survey is in `sources/data/extraction-plan.csv`.')
    return base + (' — closes: a geometry-aware extractor for this table family, tied to '
                   'the printed total on each page. The per-year survey is in '
                   '`sources/data/extraction-plan.csv`.')


def read_existing():
    with open(GAPS, 'rb') as fh:
        raw = fh.read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf-8')
    rows = list(csv.DictReader(io.StringIO(text)))
    return rows, nl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    existing, nl = read_existing()
    kept = [r for r in existing if (r.get('side') or '') != SIDE]
    mine = gap_rows()
    if not mine:
        print('nothing to register')
        return 0

    # AND AN `extraction` ROW THIS SCRIPT DID NOT AUTHOR IS KEPT, NOT DESTROYED.
    # Dropping every row of this side and rewriting its own deleted four gaps a
    # person had registered here by hand -- among them the FY2023 receipts page
    # that is blocked at 93 dpi and the tracker's own recognition blind spot,
    # both of which are still true. money-gaps.csv has several authors, and a
    # generator that owns a SIDE does not thereby own every row in it. Rows are
    # matched on their question, which is what identifies a gap.
    asked = {r['what'] for r in mine}
    inherited = [r for r in existing
                 if (r.get('side') or '') == SIDE and r['what'] not in asked]

    merged = kept + inherited + mine
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=['side', 'what', 'why'], lineterminator=nl)
    w.writeheader()
    for r in merged:
        w.writerow({k: r.get(k, '') for k in ('side', 'what', 'why')})
    out = buf.getvalue()

    current = open(GAPS, encoding='utf-8').read()
    if a.check:
        if out != current:
            print('money-gaps.csv is stale for side=%s — run: '
                  'python3 scripts/build_extraction_gaps.py' % SIDE, file=sys.stderr)
            return 1
        print('%d %s gap(s), current' % (len(mine), SIDE))
        return 0

    with open(GAPS, 'w', encoding='utf-8', newline='') as fh:
        fh.write(out)
    print('registered %d %s gap(s); %d other row(s) untouched' % (len(mine), SIDE, len(kept)))
    for r in mine:
        print('  ' + r['what'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
