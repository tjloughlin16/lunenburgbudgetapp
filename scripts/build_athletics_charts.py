#!/usr/bin/env python3
"""The athletics drill-in page's series, pre-rendered from the database.

    python3 scripts/build_athletics_charts.py            # write it
    python3 scripts/build_athletics_charts.py --check    # fail if it is stale

WHY A FILE AND NOT A QUERY. Everything here is the same for every reader until the
database is rebuilt, and D1's free tier stops at 5 million rows read a day. The page
fetches one static JSON and never touches /api/query.

THREE QUANTITIES, NEVER ADDED. `athletics_history` holds a general fund APPROPRIATION,
a revolving fund's SPENDING, and that fund's REVENUE, and a published figure of
"$335,856 through the revolving fund" was once the second plus the third. Revenue rows
are the ones whose `item` begins `REVENUE`; they are pulled out first, kept in their own
field, and `assert_no_revenue_in_spending()` refuses to write if one ever leaks into a
spending total.

RULE 11 IS THE SUBJECT. A general fund athletics line is what the town has to raise after
the fee-funded fund has paid its share, and athletics is the ONE programme where the
second half is visible. So the comparison this page exists to draw -- appropriation
against what the district's own operating workbook says the sports cost -- is a
measurement of rule 11 rather than a warning about it. It is one year, one programme, and
comparable categories only; the page says all three.

RULE 13. Every figure is recomputed from the tables rather than read off the analyses.
Where the recomputation disagrees with a sentence in `athletics.md` or
`athletics-ledger.md`, the disagreement is CARRIED IN THE PAYLOAD (`recomputed`) and
rendered on the page beside the figure, with which one is the recomputed one. Two are
known and both come from the same place: three FY2024 general fund rows were withdrawn in
commit 07aa298 as a column-mapping error after those documents were written.

WHAT IT REFUSES TO WRITE ON. Four checks, each one guarding a join that could silently
match nothing:
  1. the workbook's cost categories must sum to its own `Total Expenses`, per year, to
     the cent -- it is the source's own identity and it fixes the category split;
  2. the fund's cashbook must chain, each year's closing to the next year's printed
     `SOY BAL` -- the town's own row, not ours;
  3. every series must be non-empty;
  4. no revenue row may reach a spending total.
"""
import argparse
import collections
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/athletics.json')
REPORTS = os.path.join(ROOT, 'fy28/public/data/reports.json')

CENT = 0.005

# The workbook's cost columns, grouped for the chart. Three named categories carry the
# bulk of both years and each is separately interesting -- coaches because the general
# fund pays part of it, transportation because it MOVED, officials because the general
# fund budgets zero for it. Everything else is a residual and is drawn achromatic for
# that reason.
#
# `Assignor` and `Police/ EMS` sit in the residual rather than under Officials, even
# though a reader would file them there. That is deliberate: `athletics-ledger.md` §5
# groups them that way, and regrouping them would put a second difference into a table
# whose whole job is to isolate ONE -- the general fund side. The category is the
# workbook's own column name, `Official`, not our idea of what officiating costs.
CATEGORY = {
    'Coaches': 'Coaches',
    'Transportation': 'Transportation',
    'Official': 'Officials',
}
CAT_ORDER = ['Coaches', 'Transportation', 'Officials', 'Everything else']
COST_METRICS = ['Coaches', 'Transportation', 'Official', 'Assignor', 'Police/ EMS',
                'Uniforms', 'Equipment', 'Equipment Recon', 'Dues & Fees', 'Misc']

# The fee-category columns that hold COUNTS in every year they appear. The reduced-fee
# columns are deliberately absent: `HS Red Fee` totals 213 in FY2024 and 662.5 in FY2025,
# so it is dollars in one year and something else in the other, and rule 13 says a column
# whose meaning we cannot state is not a column we may sum.
COUNT_COLUMNS = ['Full Pay', '2nd Sibling', '3rd sibling', 'Full Waiver']

# The general fund lines the district's workbook also tracks, so the two can be set side
# by side. Everything outside this map is reported separately as UNMATCHED rather than
# folded in -- the athletic director, the trainer and insurance are real appropriations
# the workbook simply does not carry, and adding them to one side of a comparison the
# other side cannot see is the error this whole page is about.
COMPARABLE = {
    'Athletic Coaches': 'Coaches',
    'Freshman & MS Coaches': 'Coaches',
    'Freshman & Ms Coaches': 'Coaches',
    'Unified Sports Coach': 'Coaches',
    'Unified Sports,Track/Basketball Coach': 'Coaches',
    'Athletic Transportation': 'Transportation',
    'Athletic Officials': 'Officials',
    'Athletic Replacement of Uniforms': 'Uniforms',
    'Athletic Dues & Fees': 'Everything else matched',
    'Athletic Equipment/Reconditioning': 'Everything else matched',
    'Athletic New Equipment': 'Everything else matched',
    'Special Detail/Athletic Events': 'Everything else matched',
    'Athletic Expenses/Supplies': 'Everything else matched',
}
WORKBOOK_COMPARABLE = {
    'Coaches': ['Coaches'],
    'Transportation': ['Transportation'],
    'Officials': ['Official'],
    'Uniforms': ['Uniforms'],
    'Everything else matched': ['Equipment', 'Equipment Recon', 'Dues & Fees', 'Misc',
                               'Assignor', 'Police/ EMS'],
}
COMPARE_FY = 2024

# ---------------------------------------------------------------------------------------
# THE FLAG THAT SITS ABOVE THE THREE LEVELS. Where the figures a page publishes have been
# publicly contested on the record, the page says so beside them. The per-sport costs here
# come from ONE document -- the district's own athletics workbook -- and School Committee
# minutes of 24 June 2026 record a resident telling the committee that questions about what
# middle school athletics actually costs have been answered inconsistently.
#
# RULE 15a. A quote from the minutes is asserted against the minutes file on EVERY build,
# not read once and typed. The assertion is on the WORDS, normalised for the line wrapping
# the PDF extract carries, and the line number the quote starts on is computed and
# published so a reader can find it in the text we serve.
#
# RULE 13, WHICH IS WHY THE SPEAKER IS CHECKED TOO. This is public comment, recorded in the
# minutes -- it is a resident's statement, not the district's own words, and the difference
# matters. So the build also asserts that the quote sits inside that speaker's block, and
# the page attributes it that way. What the minutes establish is that the question was put
# in public and that the answers given were described on the record as inconsistent. They
# are not the district conceding a figure.
MINUTES_DOC = 'sources/meetings/text/school-committee/2026-06-24-minutes-7869.txt'
MINUTES_URL = '/docs/minutes/text/school-committee/2026-06-24-minutes-7869.txt'
MINUTES_TOWN_URL = ('https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/'
                    '_06242026-7869')
MINUTES_BOARD = 'School Committee'
MINUTES_DATE = '24 June 2026'
MINUTES_SPEAKER = 'Chris Hurlbut'
# How far the speaker's name may sit ahead of a quote for the quote to be inside their
# block. The whole statement runs a few hundred characters; anything past this and the
# attribution is a guess rather than a reading.
SPEAKER_WINDOW = 2000
MINUTES_QUOTES = [
    ('Community members have asked straightforward questions regarding the actual cost '
     'of middle school athletics and the process required to apply community raised '
     'funds towards these programs. Yet the answers have been inconsistent.'),
    ('Available data suggests that user registration fees may exceed the known cost of '
     'operating these programs'),
    ('middle school athletics were eliminated as a budget reduction of $14,415'),
]
# The reduction the minutes name is also a line in the district's own budget: the build
# checks the two against each other rather than letting a quoted figure stand alone.
MINUTES_REDUCTION_LINE = 'Freshman & MS Coaches'

# The generic words in the workbook's sport names. They are not sports, so a payment
# reading "MS" or "OOD" is not a payment attributed to a sport, and counting one as a hit
# would turn a real absence into a false presence.
SPORT_STOPWORDS = {'boys', 'girls', 'out', 'of', 'district', 'team', 'ood', 'hs', 'ms'}
# Every field on a cashbook row that carries free text or a reference. A disbursement is
# searched across all of them: the claim is that NOTHING on the row names a sport, and a
# claim about the whole row has to look at the whole row.
JOURNAL_TEXT_FIELDS = ('src_meaning', 'journal', 'ref1', 'po_ref2', 'ref3', 'reference',
                       'check_no', 'warrant', 'voucher', 'vendor', 'comments')

# The two documents this page draws, quoted so a reader can find them.
RELATED = [
    ('athletics', 'The written analysis: both sides of the money, FY14 to FY26, and why '
                  'an appropriation is not a cost'),
    ('athletics-ledger', 'Three years of the fund at transaction level — 277 postings '
                         'with vendor, check number and the clerk’s own comments'),
]


def q(c, sql, *a):
    return [dict(r) for r in c.execute(sql, a)]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fail(msg):
    sys.exit(f'build_athletics_charts: {msg}')


def _flat(text):
    """One run of whitespace is one space.

    The minutes reach us as text extracted from a PDF, so a sentence is wrapped across
    lines at whatever width the page had. Asserting a quote against the raw file would be
    asserting the line breaks, which are the extractor's and not the committee's.
    """
    return ' '.join(text.split())


def minutes_quotes():
    """Every quote this page prints, checked against the minutes file. Rule 15a.

    Returns the quote with the line of the file it starts on. Refuses to write if a quote
    is not there verbatim, or if it does not sit inside the block of the speaker the page
    attributes it to -- a quote lifted out of the wrong speaker's remarks is exactly the
    rule 13 failure of quoting a rendering rather than the source.
    """
    path = os.path.join(ROOT, MINUTES_DOC)
    if not os.path.exists(path):
        fail(f'{MINUTES_DOC} is not on disk — run scripts/sync_archive.py --pull. '
             'A quote this page prints is asserted against it on every build.')
    raw = open(path, encoding='utf-8').read().splitlines()

    # A normalised copy of the file, and the line each normalised character came from, so
    # a hit can be reported as a coordinate rather than as "it is in there somewhere".
    flat, line_at = [], []
    for n, ln in enumerate(raw, start=1):
        for word in ln.split():
            if flat:
                flat.append(' ')
                line_at.append(n)
            flat.append(word)
            line_at.extend([n] * len(word))
    flat = ''.join(flat)

    speaker_at = flat.find(MINUTES_SPEAKER)
    if speaker_at < 0:
        fail(f'{MINUTES_DOC} no longer names {MINUTES_SPEAKER}. The page attributes these '
             'words to that speaker, and an attribution that cannot be checked is not one.')

    out = []
    for quote in MINUTES_QUOTES:
        at = flat.find(_flat(quote))
        if at < 0:
            fail(f'{MINUTES_DOC} no longer contains, verbatim:\n  “{quote}”\n'
                 'Either the town republished the minutes or the extractor changed. '
                 'Nothing is published from a quote that cannot be found in its source.')
        if not 0 <= at - speaker_at <= SPEAKER_WINDOW:
            fail(f'the quote “{quote[:60]}…” is {at - speaker_at} characters from '
                 f'{MINUTES_SPEAKER} in {MINUTES_DOC}. The page says it is that '
                 'speaker’s; at that distance it is a guess.')
        out.append(dict(text=quote, line=line_at[at]))
    return out


def build():
    if not os.path.exists(DB):
        fail(f'{os.path.relpath(DB, ROOT)} is not here — run scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    # ---------------------------------------------------------------- both sides
    hist = q(c, 'SELECT fy, side, item, amount, basis, source FROM athletics_history')
    if not hist:
        fail('athletics_history is empty')
    spend = collections.defaultdict(lambda: collections.defaultdict(float))
    revenue = collections.defaultdict(float)
    rev_items = collections.defaultdict(dict)
    basis = collections.defaultdict(set)
    items = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in hist:
        fy, amt = int(r['fy']), num(r['amount'])
        if amt is None:
            continue
        if r['item'].startswith('REVENUE'):
            if r['side'] != 'revolving':
                fail(f'a REVENUE row on the {r["side"]} side in FY{fy} — the fund is the '
                     'only side of this whose receipts are published')
            revenue[fy] += amt
            rev_items[r['item']][fy] = amt
            continue
        spend[r['side']][fy] += amt
        items[r['side']][r['item']][fy] = amt
        if r['side'] == 'revolving':
            basis[fy].add(r['basis'])

    years = sorted({int(r['fy']) for r in hist})
    both = []
    for fy in years:
        b = basis.get(fy, set())
        state = ('not published' if not b
                 else 'partial' if b == {'unproven'}
                 else 'published')
        both.append(dict(
            fy=fy,
            general=round(spend['general'].get(fy, 0.0), 2),
            general_basis=('budget' if fy >= 2026 else 'restated actual'),
            revolving=round(spend['revolving'].get(fy, 0.0), 2) if state != 'not published' else None,
            revolving_state=state,
            revenue=round(revenue[fy], 2) if fy in revenue else None))

    # A total is only an all-in total in a year where both sides were published.
    for r in both:
        r['all_in'] = (round(r['general'] + r['revolving'], 2)
                       if r['revolving_state'] == 'published' else None)
        r['fund_share'] = (round(r['revolving'] / r['all_in'], 4)
                           if r['all_in'] else None)

    # RULE-BREAK GUARD. If any revenue figure ever equals a spending figure for the same
    # year, one of them has been folded into the other.
    for r in both:
        if r['revenue'] and r['revolving'] and abs(r['revenue'] - r['revolving']) < CENT:
            fail(f'FY{r["fy"]}: fund revenue and fund spending are the same number — '
                 'one has been added into the other')

    def line(side, name):
        return [dict(fy=fy, amount=round(v, 2))
                for fy, v in sorted(items[side].get(name, {}).items())]

    transport = []
    for fy in years:
        g = items['general'].get('Athletic Transportation', {}).get(fy)
        f = items['revolving'].get('Athletic Transportation', {}).get(fy)
        st = 'published' if f is not None else 'not published'
        transport.append(dict(fy=fy, general=round(g, 2) if g is not None else None,
                              fund=round(f, 2) if f is not None else None, state=st))

    coaching = []
    for fy in years:
        parts = {k: v.get(fy) for k, v in items['general'].items()
                 if COMPARABLE.get(k) == 'Coaches'}
        g = sum(v for v in parts.values() if v is not None)
        f = items['revolving'].get('Athletic Coaches', {}).get(fy)
        coaching.append(dict(
            fy=fy, general=round(g, 2) if any(v is not None for v in parts.values()) else None,
            fund=round(f, 2) if f is not None else None,
            lines=sorted(k for k, v in parts.items() if v is not None)))

    # ---------------------------------------------------- the workbook, by category
    sport = q(c, "SELECT season, level, sport, fy, metric, value, is_numeric, cell "
                 'FROM athletics_by_sport')
    if not sport:
        fail('athletics_by_sport is empty')
    by_cat = collections.defaultdict(lambda: collections.defaultdict(float))
    printed = collections.defaultdict(float)
    metric_tot = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in sport:
        if r['is_numeric'] != '1':
            continue
        v = num(r['value'])
        if v is None:
            continue
        fy = int(r['fy'])
        if r['metric'] == 'Total Expenses':
            printed[fy] += v
        if r['metric'] in COST_METRICS:
            metric_tot[fy][r['metric']] += v
            by_cat[fy][CATEGORY.get(r['metric'], 'Everything else')] += v

    cost_years = sorted(printed)
    if not cost_years:
        fail('no Total Expenses rows — the workbook join matched nothing')
    # CHECK 1: the source's own identity. Every cost column summed must equal the sheet's
    # own Total Expenses column, per year. It does, to the cent, in both years -- which is
    # what fixes the category split as the document's rather than ours.
    for fy in cost_years:
        got = sum(by_cat[fy].values())
        if abs(got - printed[fy]) > CENT:
            fail(f'FY{fy}: cost columns sum to {got:,.2f} against the workbook’s own '
                 f'Total Expenses of {printed[fy]:,.2f} — the category split no longer '
                 'reconciles to the document, so it is not the document’s split')
    categories = [dict(fy=fy, **{k: round(by_cat[fy].get(k, 0.0), 2) for k in CAT_ORDER},
                       total=round(printed[fy], 2)) for fy in cost_years]

    # ------------------------------------------------- participation and cost by sport
    ath = collections.defaultdict(float)
    cost = collections.defaultdict(float)
    for r in sport:
        if r['is_numeric'] != '1':
            continue
        v = num(r['value'])
        if v is None:
            continue
        k = (r['season'], r['level'], r['sport'], int(r['fy']))
        if r['metric'] == 'Total Athletes':
            ath[k] += v
        elif r['metric'] == 'Total Expenses':
            cost[k] += v

    part_years = sorted({k[3] for k in ath})
    by_sport = []
    for (season, level, name, fy), n in sorted(ath.items()):
        cst = cost.get((season, level, name, fy))
        by_sport.append(dict(
            season=season, level=level, sport=name, fy=fy, athletes=n,
            cost=round(cst, 2) if cst is not None else None,
            per_athlete=(round(cst / n, 2) if cst is not None and n > 0 else None)))

    participation = []
    for fy in part_years:
        for season in ('Fall', 'Winter', 'Spring'):
            for level in ('HS', 'MS'):
                n = sum(v for k, v in ath.items()
                        if k[3] == fy and k[0] == season and k[1] == level)
                participation.append(dict(fy=fy, season=season, level=level, athletes=n))
    part_totals = [dict(fy=fy,
                        total=sum(v for k, v in ath.items() if k[3] == fy),
                        hs=sum(v for k, v in ath.items() if k[3] == fy and k[1] == 'HS'),
                        ms=sum(v for k, v in ath.items() if k[3] == fy and k[1] == 'MS'))
                   for fy in part_years]

    # A negative row is the workbook subtracting out-of-district athletes. Counted as the
    # sheet counts them -- but a reader has to be told, because a bar of 649 built partly
    # out of −11 is not a headcount of anything.
    negatives = sorted(
        (dict(fy=k[3], season=k[0], level=k[1], sport=k[2], athletes=v)
         for k, v in ath.items() if v < 0), key=lambda r: (r['fy'], r['season']))

    # -------------------------------------------------------- who pays, by category
    mix, mix_years = [], []
    for fy in part_years:
        counts = {m: sum(num(r['value']) or 0 for r in sport
                         if r['is_numeric'] == '1' and int(r['fy']) == fy
                         and r['metric'] == m)
                  for m in COUNT_COLUMNS}
        if not any(counts.values()):
            continue
        mix_years.append(fy)
        total = sum(v for k, v in ath.items() if k[3] == fy)
        mix.append(dict(fy=fy, total=total,
                        unclassified=round(total - sum(counts.values()), 2),
                        **{m: counts[m] for m in COUNT_COLUMNS}))
    if not mix:
        fail('no fee-category counts — the count-column join matched nothing')

    # ------------------------------------------------------------- the fee schedule
    fees = q(c, 'SELECT fy, school_year, level, item, amount, set_on, source, '
                'source_ref, verified FROM athletic_fee_schedule ORDER BY fy, level, item')
    if not fees:
        fail('athletic_fee_schedule is empty')
    fees = [dict(fy=int(r['fy']), school_year=r['school_year'], level=r['level'],
                 item=r['item'], amount=num(r['amount']), set_on=r['set_on'],
                 source=r['source'], source_ref=r['source_ref'], verified=r['verified'])
            for r in fees]
    headline = [dict(fy=r['fy'], school_year=r['school_year'], level=r['level'],
                     amount=r['amount'], set_on=r['set_on'], source=r['source'])
                for r in fees if r['item'] == 'full_pay']

    # ------------------------------------------------------------- the fund's cashbook
    j = q(c, 'SELECT fy, eff_date, post_date, src, src_meaning, journal, ref1, '
             'po_ref2, ref3, reference, amount, comments, vendor, check_no, warrant, '
             'voucher FROM fund_1301_cash_journal ORDER BY fy, eff_date')
    if not j:
        fail('fund_1301_cash_journal is empty')
    flow, src_rows, opening = [], [], {}
    for fy in sorted({int(r['fy']) for r in j}):
        rows = [r for r in j if int(r['fy']) == fy]
        soy = [r for r in rows if r['src'] == 'SOY']
        if len(soy) != 1:
            fail(f'FY{fy}: {len(soy)} SOY BAL rows — the fund’s own opening balance is '
                 'the row this extract is checked against, and there must be exactly one')
        op = num(soy[0]['amount'])
        opening[fy] = op
        moves = [num(r['amount']) or 0 for r in rows if r['src'] != 'SOY']
        receipts = sum(v for v in moves if v > 0)
        payments = sum(v for v in moves if v < 0)
        journals = sum(num(r['amount']) or 0 for r in rows if r['src'] == 'GEN')
        flow.append(dict(fy=fy, opening=round(op, 2), receipts=round(receipts, 2),
                         payments=round(payments, 2), net=round(receipts + payments, 2),
                         closing=round(op + receipts + payments, 2),
                         journals=round(journals, 2),
                         without_journals=round(op + receipts + payments - journals, 2),
                         postings=len(rows)))
        for src in sorted({r['src'] for r in rows if r['src'] != 'SOY'}):
            src_rows.append(dict(
                fy=fy, src=src,
                meaning=next(r['src_meaning'] for r in rows if r['src'] == src),
                amount=round(sum(num(r['amount']) or 0 for r in rows if r['src'] == src), 2),
                postings=sum(1 for r in rows if r['src'] == src)))

    # CHECK 2: the chain the town prints itself. Our closing balance for one year must be
    # the opening balance the town wrote for the next. It ties to the cent, all three
    # years, and this is the only check on this page the source itself supplies.
    for a, b in zip(flow, flow[1:]):
        if abs(a['closing'] - opening[b['fy']]) > CENT:
            fail(f'FY{a["fy"]} closes at {a["closing"]:,.2f} and FY{b["fy"]} opens at '
                 f'{opening[b["fy"]]:,.2f} — the cashbook no longer chains')

    memo = [dict(fy=int(r['fy']), eff=r['eff_date'], post=r['post_date'],
                 journal=r['journal'], ref1=r['ref1'], reference=(r['reference'] or '').strip(),
                 amount=num(r['amount']), comments=r['comments'])
            for r in j if r['src'] == 'GEN']
    if not memo:
        fail('no GEN rows — the "per memo" join matched nothing')
    memo_total = round(sum(r['amount'] for r in memo), 2)

    # Vendor is populated on receipts and empty on every disbursement row. That absence is
    # a finding, so it is counted rather than described.
    disb = [r for r in j if (num(r['amount']) or 0) < 0]
    named = [r for r in disb if (r['vendor'] or '').strip()]

    # ------------------------------------------ CAN A PAYMENT BE PUT AGAINST A SPORT?
    #
    # The page states that it cannot, so the page runs the search rather than repeating a
    # sentence from an analysis. Every disbursement row, every free-text and reference
    # field on it, against the workbook's OWN sport names -- taken from the data, so a
    # sport the district adds next year is searched for without anybody remembering to.
    #
    # A search that finds nothing and a search that had nothing to look for are the same
    # printed zero, which is why both the vocabulary and the rows are asserted non-empty
    # before the count means anything.
    sport_terms = sorted({
        w for name in {k[2] for k in ath}
        for w in ''.join(ch if ch.isalpha() else ' ' for ch in name.lower()).split()
        if len(w) >= 2 and w not in SPORT_STOPWORDS})
    if not sport_terms:
        fail('no sport names came out of athletics_by_sport, so the search for a sport on '
             'a payment had nothing to look for. A zero from an empty vocabulary is not a '
             'finding.')
    if not disb:
        fail('no disbursement rows in fund_1301_cash_journal — the page says what these '
             'rows do not carry, and it may not say it about an empty set')
    # Whole words only. `CC` is the workbook's name for cross country and it is also
    # inside "accounts payable", so a substring test reported eleven payments as naming a
    # sport when not one of them does -- a false presence, which is worse than the absence
    # it would have hidden.
    term_re = {t: re.compile(r'\b' + re.escape(t) + r'\b') for t in sport_terms}
    sport_hits = []
    for r in disb:
        blob = ' '.join((r[f] or '') for f in JOURNAL_TEXT_FIELDS).lower()
        hit = sorted({t for t, rx in term_re.items() if rx.search(blob)})
        if hit:
            sport_hits.append(dict(fy=int(r['fy']), journal=r['journal'],
                                   amount=num(r['amount']), terms=hit))
    warrant_rows = [r for r in disb if r['src'] == 'APP']
    with_ref = [r for r in warrant_rows if (r['reference'] or '').strip()]
    attribution = dict(
        years=sorted({int(r['fy']) for r in disb}),
        disbursements=len(disb),
        named_vendor=len(named),
        warrant_disbursements=len(warrant_rows),
        warrant_disbursements_referenced=len(with_ref),
        fields_searched=list(JOURNAL_TEXT_FIELDS),
        sport_terms=sport_terms,
        sports=len({k[2] for k in ath}),
        sport_mentions=len(sport_hits),
        sport_hits=sport_hits)

    # ------------------------------------- rule 11, measured: one year, one programme
    gf = collections.defaultdict(float)
    unmatched = collections.defaultdict(float)
    for item, per_fy in items['general'].items():
        v = per_fy.get(COMPARE_FY)
        if v is None:
            continue
        cat = COMPARABLE.get(item)
        if cat:
            gf[cat] += v
        else:
            unmatched[item] += v
    wb = {cat: sum(metric_tot[COMPARE_FY].get(m, 0.0) for m in ms)
          for cat, ms in WORKBOOK_COMPARABLE.items()}
    if not gf or not any(wb.values()):
        fail(f'FY{COMPARE_FY}: the comparable-category join matched nothing on one side')
    compare = dict(
        fy=COMPARE_FY,
        rows=[dict(category=cat, workbook=round(wb.get(cat, 0.0), 2),
                   general=round(gf.get(cat, 0.0), 2),
                   outside=round(wb.get(cat, 0.0) - gf.get(cat, 0.0), 2))
              for cat in ('Officials', 'Coaches', 'Transportation', 'Uniforms',
                          'Everything else matched')],
        workbook_total=round(sum(wb.values()), 2),
        general_total=round(sum(gf.values()), 2),
        unmatched=[dict(item=k, amount=round(v, 2))
                   for k, v in sorted(unmatched.items(), key=lambda kv: -kv[1])],
        unmatched_total=round(sum(unmatched.values()), 2))
    compare['share'] = round(compare['general_total'] / compare['workbook_total'], 4)

    # CHECK 1b: the comparable categories must not exceed the workbook's own total.
    if compare['workbook_total'] > printed[COMPARE_FY] + CENT:
        fail(f'FY{COMPARE_FY}: comparable categories sum above the workbook’s own total')

    # -------------------------------------- THREE DOCUMENTS, THREE FIGURES, ONE YEAR
    #
    # The strongest thing on this page, and it is a DISAGREEMENT rather than a number.
    # Three documents state what athletics came to in FY2024 and no two of them agree:
    #
    #   the district's own workbook          — its printed Total Expenses, every sport
    #   the athletics revolving fund         — what it actually paid out, from its cashbook
    #   the town's general fund              — every athletics line in the budget book
    #
    # The second and third are money that left two different pots, so they may be added to
    # each other -- and their sum is well above what the first says the whole thing cost.
    # The first may NOT be added to either: it is a claim about total cost, and adding a
    # claim to a payment is the error this page exists to demonstrate.
    #
    # Levels, in the sense the site now labels them: the workbook figure is STATED, the
    # fund's payments are TRACED TO A PAYMENT, the appropriation is STATED in a budget book
    # the district wrote. Publishing the three together is what CROSS-CHECKED means when
    # the sources visibly disagree.
    flow_cmp = next((r for r in flow if r['fy'] == COMPARE_FY), None)
    wb_total = printed.get(COMPARE_FY)
    gf_total = spend['general'].get(COMPARE_FY)
    if flow_cmp is None or wb_total is None or not gf_total:
        fail(f'FY{COMPARE_FY}: one of the three sides of the disagreement is missing — '
             f'workbook {wb_total}, fund {flow_cmp is not None}, general fund {gf_total}. '
             'A three-way disagreement with two sides is not one, and an absent side must '
             'not be drawn as a small one.')
    fund_paid = abs(flow_cmp['payments'])
    if fund_paid <= 0:
        fail(f'FY{COMPARE_FY}: the revolving fund shows no payments out. That is an empty '
             'join, not a fund that spent nothing.')
    three_way = dict(
        fy=COMPARE_FY,
        workbook=round(wb_total, 2),
        fund_paid=round(fund_paid, 2),
        general=round(gf_total, 2),
        two_pots=round(fund_paid + gf_total, 2),
        over_workbook=round(fund_paid + gf_total - wb_total, 2),
        over_workbook_share=round((fund_paid + gf_total) / wb_total - 1, 4),
        sources=[
            dict(who='the district’s workbook states',
                 amount=round(wb_total, 2), level='stated',
                 what='its own printed Total Expenses across every sport',
                 table='athletics_by_sport'),
            dict(who='the revolving fund actually paid',
                 amount=round(fund_paid, 2), level='traced to a payment',
                 what='every disbursement in the fund’s cashbook that year',
                 table='fund_1301_cash_journal'),
            dict(who='the general fund carried',
                 amount=round(gf_total, 2), level='stated',
                 what='every athletics line in the district’s budget book',
                 table='athletics_history'),
        ])

    # ------------------------------- the reduction the minutes name, against the budget
    #
    # The minutes quote a figure. A quoted figure is a claim, so it is checked against the
    # district's own line rather than repeated: the last year middle school coaching was
    # funded, the budget carries exactly the amount the reduction is said to have removed.
    quotes = minutes_quotes()
    reduction_line = next(
        ((item, per_fy) for item, per_fy in items['general'].items()
         if item.lower() == MINUTES_REDUCTION_LINE.lower()), None)
    if reduction_line is None:
        fail(f'no general fund line called “{MINUTES_REDUCTION_LINE}” in '
             'athletics_history. The page checks a figure quoted from the minutes against '
             'that line, and a missing line is an unchecked quote.')
    red_item, red_by_fy = reduction_line
    red_fy = max(red_by_fy)
    reduction = dict(
        line=red_item, fy=red_fy, amount=round(red_by_fy[red_fy], 2),
        quoted=quotes[-1]['text'],
        matches=(f'${red_by_fy[red_fy]:,.0f}' in quotes[-1]['text']))
    if not reduction['matches']:
        fail(f'the minutes quote a reduction the budget line “{red_item}” does not match: '
             f'the line is {red_by_fy[red_fy]:,.2f} in FY{red_fy}. Either the quote or the '
             'line moved, and the page states that the two agree.')

    disclaimer = dict(
        board=MINUTES_BOARD, date=MINUTES_DATE, speaker=MINUTES_SPEAKER,
        doc=MINUTES_DOC, url=MINUTES_URL, town_url=MINUTES_TOWN_URL,
        quotes=quotes, reduction=reduction)

    # ------------------------------------------ where we differ from the prose, and why
    #
    # TWO OF THESE WERE RESOLVED on 7 September 2026 by correcting the analyses, and the
    # entries are gone rather than left standing as caveats: a page's job is to be current,
    # and a resolved disagreement is history. What replaces them is a CHECK, because the
    # thing that let them exist was that nothing compared the two.
    #
    # `verify_athletics.py` asserts the figures are present in the analyses. This asserts
    # the other direction -- that the SUPERSEDED figures are gone. Both are needed: a
    # document can carry the new number in one table and the old one in a sentence
    # underneath, which is exactly the shape of every defect in this project.
    for _doc, _gone, _what in (
        ('athletics.md', '314,319', 'the FY2024 general fund total'),
        ('athletics-ledger.md', '44%', 'the FY2024 share of workbook cost'),
        ('athletics-ledger.md', '65,073', 'FY2024 coaches on the general fund side'),
        ('athletics-ledger.md', '153,339', 'the FY2024 comparable general fund total'),
    ):
        _p = os.path.join(ROOT, 'sources', 'analyses', _doc)
        if _gone in open(_p, encoding='utf-8').read():
            fail(f'{_doc} still carries {_gone} for {_what}. That figure was superseded '
                 f'when commit 07aa298 withdrew three FY2024 rows. Either the correction '
                 f'was reverted or a second copy of it was missed.')

    recomputed = [
        dict(what='Whether the middle school blended fee exceeds its own top tier, FY2026',
             ours=None, published=None, boolean=True,
             where='athletics-ledger.md §8',
             why='That section reports the middle school half as unresolved, because no '
                 'document it held gave a 2025-26 middle school rate and the blended rate '
                 'therefore exceeded the only rate stated. The fee register now carries '
                 'one — $275, from School Committee minutes of 26 February 2025 — and '
                 'the blended rate recomputed below comes in under it, which is what a '
                 'blend of full pay, reduced fees and waivers has to do. On that figure '
                 'the anomaly does not arise.'),
    ]

    # The workbook's transportation total is the same quantity the two budget sides add
    # to, in both years it covers -- so it is a CHECK rather than a third series, and the
    # page can say the appropriation and the fund's share are two parts of one cost.
    for r in transport:
        wbt = metric_tot.get(r['fy'], {}).get('Transportation')
        r['cost'] = round(wbt, 2) if wbt is not None else None
        if wbt is not None and r['general'] is not None and r['fund'] is not None:
            if abs(r['general'] + r['fund'] - wbt) > CENT:
                fail(f'FY{r["fy"]}: the appropriation plus the fund’s share is '
                     f'{r["general"] + r["fund"]:,.2f} against the workbook’s '
                     f'transportation total of {wbt:,.2f} — they are no longer two parts '
                     'of one number, so the chart may not draw them as one')
        r['fund_share'] = (round(r['fund'] / wbt, 4)
                           if wbt and r['fund'] is not None else None)

    # Cost per participation. OURS, not the workbook's: it prints a cost and it prints a
    # headcount and it never divides one by the other. A participation is not a student --
    # one child in three seasons is three of these.
    for r in part_totals:
        t = printed.get(r['fy'])
        r['cost'] = round(t, 2) if t is not None else None
        r['per_participation'] = round(t / r['total'], 2) if t and r['total'] else None

    # WHAT A PARTICIPATION ACTUALLY PAID, in the one year both halves exist. The fund's
    # own year-end report gives NET user fees by level; the workbook gives participations
    # by level. Dividing is ours. Rule 11 twice over: the revenue is net of the payment
    # processor's cut, so this is what the fund banked and not what a family was charged,
    # and a blended rate must come in UNDER the top tier once waivers and sibling
    # discounts are in the pool -- which is the test.
    fee_check = []
    for lvl, item, label in (('HS', 'REVENUE — High school user fees (net)', 'High school'),
                             ('MS', 'REVENUE — Middle school user fees (net)', 'Middle school')):
        net = rev_items.get(item, {}).get(2026)
        n = next((r['hs'] if lvl == 'HS' else r['ms'])
                 for r in part_totals if r['fy'] == 2026)
        stated = next((f['amount'] for f in fees
                       if f['fy'] == 2026 and f['level'] == lvl and f['item'] == 'full_pay'),
                      None)
        if net is None or not n:
            fail(f'FY2026 {label}: no net user-fee row or no participations — the join '
                 'between the fund’s report and the workbook matched nothing')
        fee_check.append(dict(level=label, net=round(net, 2), participations=n,
                              per_participation=round(net / n, 2), stated_fee=stated,
                              under_top_tier=bool(stated and net / n < stated)))

    # ---------------------------------------------------------------- the gaps register
    gaps = q(c, 'SELECT side, what, why FROM money_gaps')
    keep = [g for g in gaps
            if any(w in (g['what'] + ' ' + g['why']).lower()
                   for w in ('athletic', 'revolving', 'special revenue fund',
                             'end of year financial report', 'play sports'))]
    if not keep:
        fail('no money_gaps row mentions athletics — rule 7c says a limit this page hits '
             'is registered there, and the join that reads them back matched nothing')

    # ----------------------------------------------------------------- the two analyses
    with open(REPORTS, encoding='utf-8') as fh:
        by_id = {r['id']: r for r in json.load(fh)['reports']}
    related = []
    for rid, why in RELATED:
        r = by_id.get(rid)
        if r is None:
            fail(f'reports.json no longer carries {rid}, which this page is built from')
        related.append(dict(id=rid, title=r['title'], why=why, words=r['words'],
                            updated=r['updated'], url=r['markdown']['url'],
                            pdf=(r.get('pdf') or {}).get('url')))

    return dict(
        generated_by='scripts/build_athletics_charts.py',
        source='sources/data/lunenburg.db — athletics_history, athletics_by_sport, '
               'athletic_fee_schedule, fund_1301_cash_journal, money_gaps',
        coverage=dict(
            history_years=years,
            cost_years=cost_years, part_years=part_years, mix_years=mix_years,
            fund_years=[r['fy'] for r in flow],
            postings=len(j), sports=len({(k[0], k[1], k[2]) for k in ath}),
            fee_rows=len(fees),
            disbursements=len(disb), disbursements_named=len(named)),
        both_sides=both,
        transport=transport,
        coaching=coaching,
        categories=categories,
        category_order=CAT_ORDER,
        by_sport=by_sport,
        participation=participation,
        participation_totals=part_totals,
        negatives=negatives,
        fee_mix=mix, count_columns=COUNT_COLUMNS,
        fees=fees, fee_headline=headline,
        fund_flow=flow, fund_sources=src_rows,
        memo_entries=memo, memo_total=memo_total,
        compare=compare,
        three_way=three_way,
        disclaimer=disclaimer,
        attribution=attribution,
        fee_check=fee_check,
        fy26_fund=dict(
            revenue=next(r['revenue'] for r in both if r['fy'] == 2026),
            spending=next(r['revolving'] for r in both if r['fy'] == 2026),
            appropriation=next(r['general'] for r in both if r['fy'] == 2026),
            all_in=next(r['all_in'] for r in both if r['fy'] == 2026)),
        recomputed=recomputed,
        gaps=[dict(side=g['side'], what=g['what'], why=g['why']) for g in keep],
        related=related,
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
                  'Run scripts/build_athletics_charts.py.')
            return 1
        print(f'ok — {rel} reproduces from the database')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    print(f'wrote {rel} — {len(d["both_sides"])} years of both sides, '
          f'{d["coverage"]["postings"]} postings, {d["coverage"]["sports"]} sports, '
          f'FY{d["compare"]["fy"] % 100} appropriation covers '
          f'{d["compare"]["share"] * 100:.0f}% of the workbook’s cost')
    return 0


if __name__ == '__main__':
    sys.exit(main())
