#!/usr/bin/env python3
"""SCHOOL SCHOLARSHIPS: the scholarship and prize funds the Town holds for its students, what
each holds, and which records cover which years. One topic page on the whole-school shelf.

    python3 scripts/build_school_scholarships.py           # write the topic payload
    python3 scripts/build_school_scholarships.py --check   # fail if it would change

TJ, 4 November 2026: *"you can build that, but dont focus on FY25. just include only that data
and show what info we dont have."* So the page leads with the funds, not a year; every figure
says which record it is from; and the coverage chart draws, fund by fund and year by year, what
we hold and what we do not.

WHAT FEEDS IT, all already in sources/data:
  trust-fund-matrix.csv     the annual report's trust fund summary, read and proven (every
                            identity the page prints closes). FY2025 only, today.
  trust-fund-balances.csv   the Treasurer's cash listing, by account, FY2024 and FY2025.
  report-trust-funds.csv    the GENERIC extract of every year's trust table: a fund named there
                            is printed that year, and its figures are not proven, so it is drawn
                            as printed-not-read and no figure from it is used.
  munis-school-journal.csv  the school ledger, FY2023-FY2026: only two of these funds appear.

THE FUND LIST IS OURS (below): one entry per donor, matched by surname, because the same fund
prints as `DORA HAVEN COWDRY SCHOLARSHIP` in one record and `Dora Haven Cowdrey Scholarship` in
another. A fund is on it when a record names it a scholarship, prize or award.
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402

ID = 'school-scholarships'
DATA = os.path.join(ROOT, 'sources', 'data')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
YEARS = list(range(2011, 2027))

# (display name, surname pattern, the trust summary's column or None, school ledger fund or None)
FUNDS = [
    ('Dora Haven Cowdry scholarship', r'cowdr', 'DORA HAVEN COWDRY SCHOLARSHIP', None),
    ('Vincent Joseph scholarship', r'vincent joseph', 'VINCENT JOSEPH SCHOLARSHIP', None),
    ('Pete Lincoln scholarship', r'lincoln', 'PETE LINCOLN SCHOLARSHIP', None),
    ('Ryan Busque scholarship', r'busque', 'RYAN BUSQUE SCHOLARSHIP', None),
    ('Beth N. Curtis memorial scholarship', r'curtis', 'BETH N CURTIS MEMORIAL SCHOLAR', None),
    ('Mabel Allen school prize', r'mabel allen', 'MABEL ALLEN SCHOOL PRIZE', None),
    ('Joseph Harwood school prize', r'harwood', 'JOSEPH HARWOOD SCHOOL', None),
    ('George Wakefield scholarship', r'wakefield', 'GEORGE WAKEFIELD SCHOLARSHIP', None),
    ('Philip Crouse scholarship', r'crouse', 'PHILIP CROUSE', None),
    ('Timothy J. Stanley scholarship', r'stanley', 'TIMOTHY J STANLEY SCHOLARSHIP', None),
    ('Scott Czelusniak memorial award', r'czelusniak', 'SCOTT CZELUSNIAK MEMORIAL AWARD', '8134'),
    ('Barbara Nelson scholarship', r'nelson', 'BARBARA NELSON SCHOLARSHIP', '8130'),
    ('Geof Lucier scholarship', r'lucier', None, None),
    ('Linde Sacksen scholarship', r'sacksen', None, None),
]


def fail(msg):
    raise SystemExit('build_school_scholarships: ' + msg)


def rows(name):
    return list(csv.DictReader(open(os.path.join(DATA, name), encoding='utf-8')))


def load():
    matrix = [r for r in rows('trust-fund-matrix.csv')]
    mfy = sorted({int(r['fy']) for r in matrix})
    held = {}            # display -> {measure: amount}, from the proven summary
    for disp, _, col, _ in FUNDS:
        if col:
            m = {r['measure']: float(r['amount'] or 0) for r in matrix if r['column'] == col}
            if not m:
                fail('%s is not on the trust fund summary: the join matched nothing' % col)
            held[disp] = m
    cover = {disp: {} for disp, _, _, _ in FUNDS}
    for r in matrix:
        for disp, pat, col, _ in FUNDS:
            if col and r['column'] == col:
                cover[disp][int(r['fy'])] = 'proven'
    for r in rows('trust-fund-balances.csv'):
        for disp, pat, _, _ in FUNDS:
            if re.search(pat, r['name'], re.I):
                cover[disp].setdefault(int(r['fy']), 'listing')
    for r in rows('report-trust-funds.csv'):
        for disp, pat, _, _ in FUNDS:
            if re.search(pat, r['label'], re.I) and int(r['fy']) in YEARS:
                cover[disp].setdefault(int(r['fy']), 'printed')
    ledger = collections.defaultdict(set)
    for r in rows('munis-school-journal.csv'):
        for disp, _, _, fund in FUNDS:
            if fund and r['fund'] == fund:
                ledger[disp].add(int(r['fiscal_year']))
    named = [d for d, _, _, f in FUNDS if f]
    if sorted(ledger) != sorted(named):
        fail('the school ledger funds changed: %s' % sorted(ledger))
    other = sorted({r['fund_name'] for r in rows('munis-school-journal.csv')
                    if re.search(r'scholar', r['fund_name'], re.I)})
    if len(other) != 2:
        fail('the school ledger now names %d scholarship funds: %s' % (len(other), other))
    return held, cover, ledger, mfy[-1]


def page():
    held, cover, ledger, last = load()
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    U = lambda v: figure(v, C.usd(v))
    N = lambda v, unit: figure(v, C.num(v), unit)
    P = lambda x: figure(x * 100, C.pct(x * 100, 0), 'percent')
    mv = {d: m['ending market value'] for d, m in held.items()}
    total = sum(mv.values())
    top = max(mv, key=mv.get)
    share = mv[top] / total
    earned = sum(m.get('net income', 0) for m in held.values())
    moved = -sum(m.get('transfers of earnings (expendable)', 0) for m in held.values())
    moved_n = sum(1 for m in held.values() if m.get('transfers of earnings (expendable)', 0))
    n_all, n_sum = len(FUNDS), len(held)
    n_ledger = len(ledger)
    # the years a report prints a summary naming these funds that we have not read and proven
    unread = sorted({y for c in cover.values() for y, s in c.items() if s == 'printed'}
                    - {y for c in cover.values() for y, s in c.items() if s == 'proven'})

    # ---- the signature: every fund on the summary, by what it holds
    rank = TP.ranking('What each fund holds', sorted(((d, round(v, 2)) for d, v in mv.items()),
                                                     key=lambda r: -r[1]), '$', highlight=top,
                      note='Market value at the close of %s, as the trust fund summary prints it.'
                           % C.fy(last), note_figures={'y': F(last)})

    # ---- what we hold, fund by fund and year by year: the gaps, drawn
    per = ['FY%02d' % (y % 100) for y in YEARS]
    tracks = []
    for disp, _, _, _ in FUNDS:
        st = []
        for y in YEARS:
            s = cover[disp].get(y)
            if s is None and y in ledger.get(disp, ()):
                s = 'ledger'
            st.append(s)
        tracks.append(TB.track(disp, st))
    tl = TB.timeline(
        'Which record covers each fund', per, [('Fund', tracks)],
        [('proven', 'Trust fund summary, read and proven', 'good'),
         ('listing', 'Treasurer’s listing: a balance only', 'muted'),
         ('ledger', 'School ledger: payments and interest', 'neutral'),
         ('printed', 'Printed in that year’s report, not yet read', 'muted', 'outline')],
        note=('A blank is a year where no record we hold names the fund.', None, ()))

    f = LD.fact
    facts = [
        f('funds', N(n_all, 'funds'), 'scholarship and prize funds any record names', 'published'),
        f('total', U(total), 'held by the funds on the trust fund summary, %s' % C.fy(last), 'published',
          label_figures={'y': F(last)}),
        f('share', P(share), 'of that in the %s' % top, 'published'),
        f('earned', U(earned), 'earned by those funds in %s' % C.fy(last), 'published',
          label_figures={'y': F(last)}),
        f('moved', U(moved), 'moved out of their earnings in %s' % C.fy(last), 'published',
          label_figures={'y': F(last)}),
        f('ledger', figure(n_ledger, '%d of %d' % (n_ledger, n_all), 'funds'), 'funds the school ledger shows',
          'published'),
        f('who', None, 'who received each award, and how much', 'gap',
          closes='A list of awards by fund and year, without names: amount and number of recipients'),
        f('unread', N(len(unread), 'years'), 'years whose trust fund summary is printed, not yet read',
          'published'),
    ]
    con = TP.conclusion
    conclusions = [
        con('One fund, the %s, holds %s of what the %d funds on the summary hold.'
            % (top, C.pct(share * 100, 0), n_sum), ['total', 'share'],
            {'s': P(share), 'n': N(n_sum, 'funds')},
            so='What the others can award each year rests on far smaller sums.'),
        con('In %s the funds earned %s and %s moved out of earnings, across %d funds.'
            % (C.fy(last), C.usd(earned), C.usd(moved), moved_n), ['earned', 'moved'],
            {'y': F(last), 'e': U(earned), 'm': U(moved), 'k': N(moved_n, 'funds')},
            so='Our reading: earnings moved out are awards paid; the summary does not say what each was.'),
        con('The school ledger shows %d of the %d funds; the rest are held and paid by the Town.'
            % (n_ledger, n_all), ['ledger'], {'a': N(n_ledger, 'funds'), 'b': N(n_all, 'funds')},
            so='The school budget documents cannot show what most of these funds award.'),
        con('%d earlier reports print these funds; only %s’s summary is read.' % (len(unread), C.fy(last)),
            ['unread'], {'n': N(len(unread), 'years'), 'y': F(last)},
            so='The history is printed and is ours to read; nothing is missing from the Town.'),
    ]

    rows_t = []
    for d, _, _, _ in FUNDS:
        m = held.get(d)
        cells = ([C.usd(m['ending market value']), C.usd(m.get('net income', 0)),
                  C.usd(-m.get('transfers of earnings (expendable)', 0))] if m else ['—', '—', '—'])
        yrs = sorted(cover[d]) + sorted(ledger.get(d, ()))
        cells.append('%s to %s' % (C.fy(min(yrs)), C.fy(max(yrs))) if yrs else '—')
        rows_t.append(dict(label=d, cells=cells))
    table = dict(caption='Every fund', views=[dict(
        key='funds', label='By fund', kinds=['ledger', 'ledger', 'ledger', 'stated'],
        columns=['Holds', 'Earned', 'Moved out', 'Named in our records'], rows=rows_t,
        note='Holds, earned and moved out are the %s trust fund summary; a dash, a fund it does not list.'
             % C.fy(last))])

    sources = [
        dict(key='summary', label='Town of Lunenburg — FY2025 annual town report, trust fund summary',
             href='/docs/town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf'),
        dict(key='matrix', label='Lunenburg Budget Project — trust-fund-matrix.csv (the summary, read)',
             href='/docs/data/trust-fund-matrix.csv'),
        dict(key='listing', label='Lunenburg Budget Project — trust-fund-balances.csv (the Treasurer’s listing)',
             href='/docs/data/trust-fund-balances.csv'),
        dict(key='generic', label='Lunenburg Budget Project — report-trust-funds.csv (every year, not yet read)',
             href='/docs/data/report-trust-funds.csv'),
        dict(key='journal', label='Lunenburg Budget Project — munis-school-journal.csv (the school ledger)',
             href='/docs/data/munis-school-journal.csv'),
    ]
    cite = TP.cite
    return TP.page(
        ID,
        'The Town holds %d scholarship and prize funds for its students; no record we hold says who '
        'receives them.' % n_all,
        facts, conclusions, chart=rank, table=table, sources=sources,
        finding_figures={'n': N(n_all, 'funds')},
        flow=['finding', cite(('chart', 0), 'summary', 'matrix'), cite('ladder', 'matrix', 'journal'),
              cite(tl, 'matrix', 'listing', 'generic', 'journal'), 'related',
              cite(('table', 0), 'matrix', 'listing', 'journal'), 'sources'],
        draft=None if ID in REG.TOPICS else dict(title='School scholarships', home='school-all-funds'))


def render():
    return json.dumps(page(), ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('school scholarships: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
