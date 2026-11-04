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


def history():
    """The proven rows, every year: scripts/extract_scholarship_funds.py. Prize-fund accounts only;
    the Unitil stock holdings are a second account of two prizes and pay nothing out."""
    out = [r for r in rows('scholarship-funds.csv') if r['account'] == 'fund']
    named = {d for d, _, _, _ in FUNDS}
    stray = {r['fund'] for r in out} - named
    if stray:
        fail('scholarship-funds.csv names funds not on FUNDS: %s' % sorted(stray))
    if not out:
        fail('scholarship-funds.csv holds no rows: run extract_scholarship_funds.py')
    return out


def _norm(t):
    return ' '.join(t.split()).lower()


def purposes():
    """What each fund is for, QUOTED: every quote is re-found in the text it came from, on every
    build, or the page does not build (rule 9 -- recomputed, not re-read)."""
    out = {}
    for r in rows('scholarship-purposes.csv'):
        if r['fund'] not in {d for d, _, _, _ in FUNDS}:
            fail('scholarship-purposes.csv: %r is not on FUNDS' % r['fund'])
        t = open(os.path.join(ROOT, r['text']), encoding='utf-8', errors='ignore').read()
        if r['text'].endswith('.json'):
            t = ' '.join(s['text'] for s in json.loads(t)['segments'])
        if _norm(r['purpose']) not in _norm(t):
            fail('%s: the quote %r is not in %s' % (r['fund'], r['purpose'], r['text']))
        out[r['fund']] = r
    return out


def page():
    held, cover, ledger, last = load()
    hist = history()
    why = purposes()
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    U = lambda v: figure(v, C.usd(v))
    N = lambda v, unit: figure(v, C.num(v), unit)
    P = lambda x: figure(x * 100, C.pct(x * 100, 0), 'percent')
    OF = lambda a, b, unit: figure(a, '%d of %d' % (a, b), unit)

    years = sorted({int(r['fy']) for r in hist})
    y0, y1 = years[0], years[-1]
    num = lambda v: float(v) if v not in ('', None) else None
    paid = collections.defaultdict(lambda: collections.defaultdict(float))
    earned = collections.defaultdict(float)
    by = collections.defaultdict(list)
    for r in hist:
        fy = int(r['fy'])
        if num(r['paid_out']) is not None:
            paid[r['fund']][fy] += num(r['paid_out'])
        earned[r['fund']] += num(r['net_earnings']) or 0
        by[r['fund']].append(r)
        cover[r['fund']][fy] = 'proven'
    tot = {f: sum(v.values()) for f, v in paid.items()}
    total = sum(tot.values())
    top = max(tot, key=tot.get)
    year_paid = {y: sum(paid[f].get(y, 0) for f in paid) for y in years}
    year_earned = {y: sum(num(r['net_earnings']) or 0 for r in hist if int(r['fy']) == y) for y in years}
    none_years = [y for y in years if year_paid[y] == 0]
    # A FUND THAT RAN DOWN: it once held more than $1,000 and its last proven balance is under $200.
    # Both thresholds are ours, chosen to name the funds whose awards have outrun their balances.
    peak = {f: max(num(r['ending_cash']) or 0 for r in l) for f, l in by.items()}
    last_row = {f: max(l, key=lambda r: int(r['fy'])) for f, l in by.items()}
    end = {f: num(last_row[f]['ending_cash']) for f in by}
    ran_down = sorted(f for f in by if peak[f] > 1000 and end[f] < 200)
    first_row = {f: min(l, key=lambda r: int(r['fy'])) for f, l in by.items()}
    # STATED BY A DOCUMENT. A caption is a finding aid, not a record (CLAUDE.md, searching what the
    # town said), so a purpose heard only in a recording is counted on its own, never as stated.
    stated = [f for f, r in why.items() if r['kind'] != 'transcript' and 'no purpose printed' not in r['note']]
    heard = [f for f, r in why.items() if r['kind'] == 'transcript']
    n_all = len(FUNDS)
    # A SHORT NAME for prose: the donor's surname. Labels and claims have character budgets.
    short = lambda d: 'the %s fund' % [w for w in d.split() if w[0].isupper() and len(w) > 2][-1]

    # ---- THE SIGNATURE: what left the funds each year, by fund. Five tracks is the palette, so the
    # four largest payers are drawn and every other fund is one band.
    order = sorted(tot, key=lambda f: -tot[f])
    big, rest = order[:4], order[4:]
    x = [C.fy(y) for y in years]
    tracks = [TP.track(f, [round(paid[f][y], 2) if y in paid[f] else None for y in years])
              for f in big]
    tracks.append(TP.track('The other funds', [round(sum(paid[f].get(y, 0) for f in rest), 2)
                                                for y in years]))
    sig = TP.series('Paid out each year, by fund', x, tracks, '$', kind='bar', stacked=True,
                    totals=True, decimals=0,
                    note='Money that left each fund, net of what came in, as the trust fund summary '
                         'prints it. That it was awards is our reading.')
    flows = TP.series('Earned against paid out', x,
                      [TP.track('Earned', [round(year_earned[y], 2) for y in years]),
                       TP.track('Paid out', [round(year_paid[y], 2) for y in years])],
                      '$', kind='line', decimals=0,
                      note='Every fund read that year, summed. A year with fewer funds read is lower '
                           'on both lines.')

    # ---- WHAT EACH FUND HOLDS NOW, by the same measure the other charts use: ending cash at the close
    # of the last year read. TJ, 4 November 2026: "a viz/chart of how much each fund currently has is
    # still useful ... that was a very obvious thing to see". Only funds read in that year are ranked,
    # so the bars are one year's balances; a fund last read earlier is named in the note, not drawn.
    now = sorted(((d, round(end[d], 2)) for d in by if int(last_row[d]['fy']) == y1),
                 key=lambda r: -r[1])
    older = sorted(d for d in by if int(last_row[d]['fy']) != y1)
    hold = TP.ranking('What each fund holds', now, '$', highlight=now[0][0],
                      note='Ending cash at the close of %s, as the trust fund summary prints it.%s'
                           % (C.fy(y1), (' Not read for that year: %s.' % ', '.join(older))
                              if older else ''),
                      note_figures={'y': F(y1)})

    f = LD.fact
    facts = [
        f('paid', U(total), 'paid out by the funds, %s to %s' % (C.fy(y0), C.fy(y1)), 'published',
          label_figures={'a': F(y0), 'b': F(y1)}),
        f('top', P(tot[top] / total), 'of that from %s' % short(top), 'published'),
        f('topearned', U(earned[top]), 'earned by %s in the same years' % short(top), 'published'),
        f('randown', N(len(ran_down), 'funds'), 'funds that once held over $1,000 and now hold under $200',
          'published', allow=('1,000', '200')),
        f('none', OF(len(none_years), len(years), 'years'), 'years in which no fund paid anything out',
          'published'),
        f('read', OF(len(years), len(years), 'years'), 'years whose trust fund summary is read and proven',
          'published'),
        f('why', OF(len(stated), n_all, 'funds'), 'funds whose purpose a record we hold states',
          'published'),
        f('who', None, 'who received each award, and how much', 'gap',
          closes='A list of awards by fund and year, without names: amount and number of recipients'),
    ]
    con = TP.conclusion
    worst = min(ran_down, key=lambda f: end[f])
    conclusions = [
        con('%d funds that once held over $1,000 each now hold under $200.' % len(ran_down),
            ['randown'], {'n': N(len(ran_down), 'funds')}, allow=('1,000', '200'),
            so='Those awards cannot continue at their old size from these funds; %s holds %s.'
               % (short(worst), C.usd(end[worst])), so_figures={'v': U(end[worst])}),
        con('%s paid out %s and earned %s in the years read.' % (short(top)[0].upper() + short(top)[1:], C.usd(tot[top]),
                                                                    C.usd(earned[top])),
            ['top', 'topearned'], {'p': U(tot[top]), 'e': U(earned[top])},
            so='The largest fund pays out less than it earns, so it has grown while %d smaller ones ran down.'
               % len(ran_down), so_figures={'n': N(len(ran_down), 'funds')}),
        con('In %d of %d years no fund paid anything out.' % (len(none_years), len(years)), ['none'],
            {'n': N(len(none_years), 'years'), 'd': N(len(years), 'years')},
            so='Those zeros are printed, not missing; the summary does not say why nothing was paid.'),
        con('A record we hold states the purpose of %d of the %d funds.' % (len(stated), n_all), ['why'],
            {'a': N(len(stated), 'funds'), 'b': N(n_all, 'funds')},
            so='A meeting recording suggests %d more; the rest are not in the reports or minutes searched.'
               % len(heard), so_figures={'h': N(len(heard), 'funds')}),
    ]

    # ---- every fund, its fifteen years in four columns
    rows_t = []
    for d in sorted(FUNDS, key=lambda t: -tot.get(t[0], -1)):
        d = d[0]
        if d not in by:
            rows_t.append(dict(label=d, cells=['—', '—', '—', '—']))
            continue
        lr, fr = last_row[d], first_row[d]
        rows_t.append(dict(label=d, cells=[
            C.usd(tot.get(d, 0)), C.usd(earned[d]),
            '%s (%s)' % (C.usd(end[d]), C.fy(int(lr['fy']))),
            ('%d, %s to %s' % (len(by[d]), C.fy(int(fr['fy'])), C.fy(int(lr['fy'])))
             if fr is not lr else '1, %s' % C.fy(int(lr['fy'])))]))
    table = dict(caption='Every fund', views=[dict(
        key='funds', label='By fund', kinds=['ledger', 'ledger', 'ledger', 'ledger'],
        columns=['Paid out', 'Earned', 'Holds, last year read', 'Years read'], rows=rows_t,
        note='Summed over the years each fund is read and proven. A dash: no year proves a row for it.')])
    rows_p = []
    for d, _, _, _ in FUNDS:
        r = why.get(d)
        if r:
            # The YEAR here is the document's calendar year, never a fiscal year.
            where = {'transcript': 'School Committee recording, %s, captions' % r['year'],
                     'minutes': 'School Committee minutes, %s, p. %s' % (r['year'], r['page']),
                     }.get(r['kind'], '%s, %s, p. %s' % (r['kind'], r['year'], r['page']))
            q = '“%s”' % r['purpose']
            if 'no purpose printed' in r['note']:
                q += ': the award’s name; no purpose printed'
            rows_p.append(dict(label=d, cells=[q, where]))
        else:
            rows_p.append(dict(label=d, cells=['No record we hold states it', '—']))
    table_p = dict(caption='What each is for', views=[dict(
        key='why', label='Purpose', kinds=['stated', 'stated'], columns=['In the record’s words', 'Record'],
        rows=rows_p, note='Quoted; each quote is re-found in its document on every build. Recordings are '
                          'machine captions: a finding aid, not a record.')])

    # ---- which record covers each fund, year by year
    per = ['FY%02d' % (y % 100) for y in YEARS]
    tl_tracks = []
    for disp, _, _, _ in FUNDS:
        st = []
        for y in YEARS:
            s_ = cover[disp].get(y)
            if s_ is None and y in ledger.get(disp, ()):
                s_ = 'ledger'
            st.append(s_)
        tl_tracks.append(TB.track(disp, st))
    tl = TB.timeline(
        'Which record covers each fund', per, [('Fund', tl_tracks)],
        [('proven', 'Trust fund summary, read and proven', 'good'),
         ('listing', 'Treasurer’s listing: a balance only', 'muted'),
         ('ledger', 'School ledger: payments and interest', 'neutral'),
         ('printed', 'Printed in that year’s report, not proven', 'muted', 'outline')],
        note=('A blank is a year where no record we hold names the fund.', None, ()))

    sources = [
        dict(key='reports', label='Town of Lunenburg — annual town reports, trust fund summaries',
             href='/docs/town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf'),
        dict(key='funds', label='Lunenburg Budget Project — scholarship-funds.csv (every year, read and proven)',
             href='/docs/data/scholarship-funds.csv'),
        dict(key='purposes', label='Lunenburg Budget Project — scholarship-purposes.csv (each purpose, quoted)',
             href='/docs/data/scholarship-purposes.csv'),
        dict(key='minutes', label='School Committee — minutes of 12 June 2024 and 8 January 2025',
             href='/docs/meetings/school-committee/2025-01-08-minutes-6948.pdf'),
        dict(key='matrix', label='Lunenburg Budget Project — trust-fund-matrix.csv (FY2025, read)',
             href='/docs/data/trust-fund-matrix.csv'),
        dict(key='listing', label='Lunenburg Budget Project — trust-fund-balances.csv (the Treasurer’s listing)',
             href='/docs/data/trust-fund-balances.csv'),
        dict(key='journal', label='Lunenburg Budget Project — munis-school-journal.csv (the school ledger)',
             href='/docs/data/munis-school-journal.csv'),
    ]
    cite = TP.cite
    return TP.page(
        ID,
        'The scholarship funds paid out %s in %s–%s; %d funds that paid awards now hold under $200 each.'
        % (C.usd(round(total)), C.fy(y0), C.fy(y1), len(ran_down)),
        facts, conclusions, chart=sig, also=(flows, hold), tables=(table, table_p), sources=sources,
        finding_figures={'t': U(round(total)), 'a': F(y0), 'b': F(y1), 'n': N(len(ran_down), 'funds')},
        finding_allow=('200',),
        flow=['finding', cite(('chart', 0), 'reports', 'funds'), cite(('chart', 2), 'reports', 'funds'),
              cite('ladder', 'funds', 'purposes'), cite(('chart', 1), 'reports', 'funds'), cite(('table', 0), 'funds', 'matrix'),
              cite(('table', 1), 'purposes', 'minutes', 'reports'),
              cite(tl, 'funds', 'listing', 'journal', 'matrix'), 'related', 'sources'],
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
