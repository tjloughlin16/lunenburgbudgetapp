#!/usr/bin/env python3
"""What the town picked up when a grant stopped paying for it.

THE QUESTION THIS ANSWERS. CLAUDE.md rule 11 says a budget line is NET and that a line can
rise because the thing got more expensive OR because a grant that was paying part of it
ended -- and that the two look identical on the expense side. That was written as a warning
with one worked example. DESE publishes the split, so it can be measured across every
function code instead.

WHAT THE SOURCE IS. `dese_function_expenditure`, DESE's End of Year Financial Report, which
attributes each dollar of district spending to the general fund or to grants and revolving
funds. This is the document rule 11 names as the thing that would settle the question, and
it is a statutory return: the schema is not the filer's to choose.

WHAT IT STILL DOES NOT SAY, and this bounds every sentence on the page:

  * WHICH grant. A fund total is not a grant.
  * WHICH post. A dollar attributed to a fund is not a person, and function 2330 falling
    in one fund and rising in another does not establish that anybody moved.
  * THAT THE SAME ACTIVITY CONTINUED. A general fund rise beside a grant fall is
    consistent with the town picking up a cost AND with two unrelated things happening in
    one function in one year.

THE TRAP THIS SCRIPT EXISTS TO AVOID, found while writing it. Across FY2024->FY2025 the
aggregate reads: grants -$2,023,188, general fund +$1,999,627, total -$23,561. That looks
like the town replacing almost exactly what the grants stopped paying, and it is NOT what
happened. Decomposed:

    8 functions   grants -1,127,647   general fund +1,136,013   <- a swap
    8 functions   grants -1,542,511   general fund   -606,553   <- both fell

and the largest general fund increase in the year is Insurance for Active Employees at
+$3,026,556, which no grant was ever paying. The aggregate near-identity is two unrelated
movements landing on similar numbers. So this script NEVER reports a district-wide netting;
it reports the swap and the reduction separately, and counts the functions in each.

    python3 scripts/build_grant_unwinding.py
    python3 scripts/build_grant_unwinding.py --check
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'grant-unwinding.json')
LEA = '01620000'

# A district does not lose its whole reporting history. If the query returns a handful of
# years something has changed underneath and writing it would publish a shorter series as
# though it were the whole record.
MIN_YEARS = 12

MINUTES = 'sources/meetings/text'

# WHAT THE TOWN SAID, rule 15a. This page measures grants falling and the general fund
# rising; the meeting archive is where anybody said out loud whether that was the plan.
# Every quote here is checked against the extracted minutes on every run, and a miss is
# fatal -- a quote is a claim about a document, and rule 13 says quote the source rather
# than your rendering of it.
#
# THESE ARE STATEMENTS OF INTENT AND OF BELIEF, NOT MEASUREMENTS. CLAUDE.md rule 7: "A
# document stating intent is evidence of intent, not of outcome." Nothing below tests
# whether what was said matches what the state's figures show, and the page says so.
QUOTES = [
    dict(key='loss', board='school-committee', date='2023-11-15', kind='minutes',
         doc='3952',
         quote='We have a loss of $650,000 in ESSER funds, this is much more significant '
               'than we expected.',
         why='Said while the FY2025 budget was being developed -- the year DESE later '
             'reports the largest grant fall on record. It is the district naming the '
             'quantity in advance.'),
    dict(key='insurance', board='school-committee', date='2024-01-17', kind='minutes',
         doc='6337',
         quote='We are anticipating a 10% increase in health insurance to be $500,000, '
               'Contractual increases of $400,000 and the loss of ESSER funds of '
               '$600,000. While we knew ESSER funds would not be continuing, the increase '
               'in health insurance was unexpected.',
         why='The two movements this page insists are separate, named separately in the '
             'same paragraph by the people doing the budget. The insurance rise and the '
             'grant loss are one sentence apart and are not the same event.'),
    dict(key='burden', board='school-committee', date='2024-05-22', kind='minutes',
         doc='6581',
         quote='I personally did not feel it appropriate to transfer the burden of that '
               'money from the federal government grants on to the backs of Lunenburg '
               'taxpayers.',
         why='The swap-or-reduction question, put as policy, by the Chair, after the '
             'override passed. It says what was intended. It does not say what happened, '
             'and DESE reports both outcomes in the same year.'),
    dict(key='paras', board='school-committee', date='2024-06-12', kind='minutes',
         doc='6615',
         quote='These cuts do equal the ESSER funds when cuts are made per contract.',
         why='Said in the same passage as a list of the posts being cut. The page reports '
             'this beside the state figures rather than against them: a count of posts '
             'and a fund total are different quantities.'),
    # FOUND BY THE PERSONA REVIEW, and included because of what it costs to leave out.
    # `notes/process/PERSONAS.md`: "for every category the report says underspent or
    # overspent, search the meeting archive for what people said about that thing in the
    # same year" -- and a reader with a library problem will find the library line whether
    # this page addresses it or not.
    dict(key='library', board='school-committee', date='2026-03-10', kind='minutes',
         doc='7706',
         quote='Ms. Cameron reflected on the impact budget cuts have had on the schools '
               'over the years, including the elimination of a librarian position at the '
               'Primary school',
         why='One of the largest reductions in FY2025 is a line DESE calls Other '
             'Instructional Materials (Libraries). THESE ARE NOT THE SAME THING and this '
             'page cannot connect them: that line is materials rather than posts, the '
             'speaker names no year, and DESE reports dollars against a function rather '
             'than positions. It is here because a resident who remembers a librarian '
             'going will find the library line, and an unaddressed number is worse than '
             'an addressed one.'),
    dict(key='beyond', board='school-committee', date='2025-09-03', kind='minutes',
         doc='7385',
         quote='So we didn ’t cut beyond ESSER, which is a really important thing to '
               'remember',
         why='A year later, the same claim in retrospect. Quoted with the space the '
             'extracted text carries, because that is what the document renders to.'),
]

# The terms run against the meeting archive for this page. THE COUNTS ARE NOT TYPED HERE:
# a grep that finds nothing prints nothing, and nothing reads as "nobody said it".
SEARCHED = ['ESSER', 'ARPA', 'circuit breaker', 'grant funded', 'one-time funds',
            'federal grant', 'Title I', 'revolving']


def q(db, sql, *a):
    return db.execute(sql, a).fetchall()


def fail(msg):
    raise SystemExit('%s. Nothing written.' % msg)


def said_in_meetings():
    """Every quote, re-read out of the extracted minutes on this run.

    A quote typed into a page is exactly the defect rule 2 is about, one layer up: it is a
    figure about a document. So the text is asserted against the file, and a miss stops
    the build rather than publishing a sentence nobody can find."""
    out = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here -- a quote on this page is attributed to a document '
                 'that is not in the archive' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            fail('the quote attributed to %s %s is no longer in %s -- quote the source, '
                 'never your rendering of it' % (spec['board'], spec['date'], rel))
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'],
            cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_%s%s%s-%s'
                 % (spec['date'][5:7], spec['date'][8:10], spec['date'][:4], spec['doc'])))
    return out


def searched():
    """Run each term, and report the DENOMINATOR with it.

    Same index and same matching as scripts/search_minutes.py. A quarter of what the town
    has published is an image scan with no text layer, so an empty result is a statement
    about the readable archive and never about the town."""
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here -- a search of nothing is not a '
             'search')
    rows = list(csv.DictReader(open(idx, encoding='utf-8')))
    readable, dates = [], []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
            if r.get('date'):
                dates.append(r['date'])
    if not readable:
        fail('no meeting document is readable -- refusing to publish a count of what '
             'nobody said')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    terms = [dict(term=t,
                  documents=sum(1 for b in bodies if re.search(re.escape(t), b, re.I)))
             for t in SEARCHED]
    if not dates:
        fail('no meeting document carries a date -- the span cannot be typed')

    # THE DENOMINATOR IS NOT "how many .txt files exist". An image scan extracts to an
    # empty file, so counting files says 12,014 readable where the measured figure is
    # 8,899 -- a coverage claim a third too generous, in the one place on this page where
    # an empty result is being reported as an empty result. `minutes-searchable.csv` is
    # the generated authority for it and is read rather than recomputed.
    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        fail('sources/data/minutes-searchable.csv is not here -- the searchable share '
             'cannot be typed')
    tally = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            tally[k] += int(r[k] or 0)
    if not tally['searchable'] or tally['held'] != tally['searchable'] + tally['unsearchable']:
        fail('minutes-searchable.csv does not reconcile -- refusing to publish a '
             'coverage figure that does not add up')
    return dict(terms=terms, text_files_present=len(readable), published=len(rows),
                held=tally['held'], searchable=tally['searchable'],
                unsearchable=tally['unsearchable'], image_scan=tally['image_scan'],
                searchable_share=round(tally['searchable'] / tally['held'], 4),
                first_date=min(dates), last_date=max(dates))


def build():
    if not os.path.exists(DB):
        raise SystemExit('%s is missing. Run scripts/build_db.py.' % DB)
    db = sqlite3.connect(DB)

    # ---- the frame: both funds, every year -----------------------------------------
    totals = q(db, """
        SELECT fy, SUM(gen_fund), SUM(grants_revolving), SUM(total)
        FROM dese_function_expenditure WHERE lea=? AND level='total'
        GROUP BY fy ORDER BY fy""", LEA)
    if len(totals) < MIN_YEARS:
        raise SystemExit('only %d years of district totals; expected at least %d. '
                         'Nothing written.' % (len(totals), MIN_YEARS))
    series = [{'fy': fy, 'gen_fund': g or 0, 'grants': gr or 0, 'total': t or 0,
               'town_share': round(100.0 * (g or 0) / (t or 1), 2)} for fy, g, gr, t in totals]

    # ---- every year-on-year step, per function, classified --------------------------
    steps = q(db, """
        SELECT a.fy, a.func_code, a.func_desc, a.in_out_dist,
               a.gen_fund, a.grants_revolving, a.total,
               b.gen_fund, b.grants_revolving, b.total
        FROM dese_function_expenditure a
        JOIN dese_function_expenditure b
          ON a.func_code=b.func_code AND a.lea=b.lea AND a.level=b.level
             AND a.in_out_dist=b.in_out_dist AND b.fy=a.fy+1
        WHERE a.lea=? AND a.level='detail'
        ORDER BY a.fy, a.func_code""", LEA)
    if not steps:
        raise SystemExit('the year-on-year join matched no functions. A join that matches '
                         'nothing looks exactly like a district that never moved money. '
                         'Nothing written.')

    years = {}
    for (fy, fc, fd, io, g0, gr0, t0, g1, gr1, t1) in steps:
        g0, gr0, t0 = g0 or 0, gr0 or 0, t0 or 0
        g1, gr1, t1 = g1 or 0, gr1 or 0, t1 or 0
        dgr, dg, dt = gr1 - gr0, g1 - g0, t1 - t0
        # THE THREE CASES, and they must never be summed together.
        if dgr < 0 and dg > 0:
            kind = 'swap'          # grants fell, the town's share rose
        elif dgr < 0 and dg <= 0:
            kind = 'reduction'     # grants fell and nothing replaced them
        elif dgr > 0:
            kind = 'grant_growth'
        else:
            kind = 'other'
        y = years.setdefault(fy + 1, {'fy': fy + 1, 'swap': [], 'reduction': [],
                                      'grant_growth': [], 'other': []})
        # The year is stamped HERE, on every item, rather than on the swaps afterwards.
        # It was set in a later loop that walked the swap lists only, so an item that
        # reached the payload by any other route carried no year -- the same dict, with
        # different keys depending on which list happened to be read first.
        y[kind].append({'fy': fy + 1, 'func_code': fc, 'func_desc': fd, 'in_out': io,
                        'd_grants': round(dgr), 'd_gen_fund': round(dg),
                        'd_total': round(dt)})

    def tally(items, key):
        return round(sum(i[key] for i in items))

    # THE FOUR CLASSES MUST ACCOUNT FOR EVERY MATCHED FUNCTION. `other` -- grants did not
    # move at all -- is the largest single class by count in most years, and leaving it out
    # would let a reader add three numbers, get something short of the aggregate, and have
    # no way of knowing which functions were missing. It is also where the FY2025 trap
    # lives: the year's largest general fund increase sits outside the swap entirely.
    by_year = []
    for fy in sorted(years):
        y = years[fy]
        row = {'fy': fy}
        for kind in ('swap', 'reduction', 'grant_growth', 'other'):
            row[kind] = {'n': len(y[kind]), 'd_grants': tally(y[kind], 'd_grants'),
                         'd_gen_fund': tally(y[kind], 'd_gen_fund')}
        # The aggregate, computed here ONCE and labelled, so the page can show what it
        # would have said and why that reading is wrong -- rather than a reader forming it
        # by adding the classes up.
        every = [i for kind in ('swap', 'reduction', 'grant_growth', 'other')
                 for i in y[kind]]
        row['aggregate'] = {
            'n': len(every), 'd_grants': tally(every, 'd_grants'),
            'd_gen_fund': tally(every, 'd_gen_fund'), 'd_total': tally(every, 'd_total'),
            'is_a_finding': False,
        }
        by_year.append(row)

    latest = max(years)
    detail = {k: sorted(years[latest][k], key=lambda i: i['d_grants'])
              for k in ('swap', 'reduction', 'grant_growth', 'other')}

    # THE LARGEST GENERAL FUND MOVEMENTS OF THE LATEST YEAR, whatever class they fall in.
    # Without these the page can only show the functions where a grant moved, which is
    # exactly the selection that makes the aggregate look like a swap.
    every_latest = [i for k in ('swap', 'reduction', 'grant_growth', 'other')
                    for i in years[latest][k]]
    gen_fund_rises = sorted(every_latest, key=lambda i: -i['d_gen_fund'])[:6]
    total_falls = sorted(every_latest, key=lambda i: i['d_total'])[:6]

    # ---- the biggest single swaps in the whole record -------------------------------
    allswaps = [i for fy in years for i in years[fy]['swap']]
    biggest = sorted(allswaps, key=lambda i: i['d_grants'])[:15]

    # ---- the document, read out of the archive rather than typed --------------------
    # Rule 12: the address, the publisher's own filename and the sha256 travel with the
    # figure. Rule 2: none of the three is typed here. A miss is fatal rather than an
    # empty string, because a citation that silently loses its hash is worse than none.
    doc = None
    with open(MANIFEST, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row['key'].endswith('district-expenditures-by-function.xlsx'):
                doc = {'path': 'sources/' + row['key'], 'sha256': row['sha256'],
                       'bytes': int(row['bytes']), 'url': row['upstream'],
                       'docs_url': '/docs/' + row['key']}
    if not doc:
        raise SystemExit('district-expenditures-by-function.xlsx is not in %s. A figure '
                         'without its document is not publishable. Nothing written.'
                         % os.path.relpath(MANIFEST, ROOT))

    hits = searched()
    first, last = series[0], series[-1]
    return {
        'about': 'Every dollar of Lunenburg school spending, split by the fund that paid '
                 'it, from DESE’s End of Year Financial Report.',
        'source': dict(doc, **{
            'table': 'dese_function_expenditure',
            'publisher': 'Massachusetts Department of Elementary and Secondary Education',
            'lea': LEA,
            'note': 'A statutory return. DESE sets the schema, not the district.',
        }),
        'fy_first': first['fy'], 'fy_last': last['fy'],
        'series': series,
        'town_share_first': first['town_share'],
        'town_share_last': last['town_share'],
        'town_share_points': round(last['town_share'] - first['town_share'], 2),
        # A COUNTERFACTUAL, labelled as one everywhere it is used.
        'counterfactual': {
            'what': 'What the general fund would have carried in %d if the split had '
                    'stayed at its %d share.' % (last['fy'], first['fy']),
            'gen_fund_actual': round(last['gen_fund']),
            'gen_fund_at_first_share': round(last['total'] * first['gen_fund'] / first['total']),
            'difference': round(last['gen_fund'] - last['total'] * first['gen_fund'] / first['total']),
            'is_measurement': False,
        },
        'by_year': by_year,
        'latest_year': latest,
        'latest_gen_fund_rises': gen_fund_rises,
        'latest_total_falls': total_falls,
        'latest_detail': detail,
        'biggest_swaps': biggest,
        'said': said_in_meetings(),
        'searched': hits['terms'],
        'minutes': {k: hits[k] for k in
                    ('published', 'held', 'searchable', 'unsearchable', 'image_scan',
                     'searchable_share', 'text_files_present', 'first_date', 'last_date')},
        'not_established': [
            'Which grant. DESE reports a fund total; it does not name a grant.',
            'Which post. A dollar attributed to a fund is not a person, and a function '
            'falling in one fund while rising in another does not establish that anybody '
            'moved between them.',
            'That the same activity continued. A general fund rise beside a grant fall is '
            'equally consistent with the town picking up a cost and with two unrelated '
            'things happening in one function in one year.',
            'A district-wide netting. In FY2025 the aggregate reads as though the town '
            'replaced almost exactly what grants stopped paying; decomposed, half the '
            'grant fall was replaced and half simply stopped, and the largest general '
            'fund increase that year was employee insurance, which no grant was paying.',
        ],
        'closes': 'Nothing published maps a grant to the posts it paid for. DESE’s '
                  'End of Year Financial Report is the furthest the public record goes: '
                  'it separates the funds and stops there. The district’s own grant '
                  'award letters and its end-of-grant reports would name the positions.',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()

    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT))
            return 1
        with open(OUT, encoding='utf-8') as fh:
            have = json.load(fh)
        if have != data:
            print('STALE %s — run: python3 scripts/build_grant_unwinding.py'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    y = data['by_year'][-1]
    print('%s: %d years, %d..%d'
          % (os.path.relpath(OUT, ROOT), len(data['series']), data['fy_first'], data['fy_last']))
    print("  the town's share of school spending: %.1f%% -> %.1f%%  (%+.1f points)"
          % (data['town_share_first'], data['town_share_last'], data['town_share_points']))
    print('  FY%d: %d functions swapped (grants %s, town %s); %d reduced (grants %s, town %s)'
          % (y['fy'], y['swap']['n'], format(y['swap']['d_grants'], ','),
             format(y['swap']['d_gen_fund'], ','), y['reduction']['n'],
             format(y['reduction']['d_grants'], ','), format(y['reduction']['d_gen_fund'], ',')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
