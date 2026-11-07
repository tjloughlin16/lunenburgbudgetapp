#!/usr/bin/env python3
"""THE EARLY LEARNING CENTER (ELC): what we hold, where it comes from, and when things happened.

    python3 scripts/build_early_learning_center.py           # write the markdown and the payload
    python3 scripts/build_early_learning_center.py --check   # fail if either is stale

    sources/analyses/early-learning-center.md    /analysis/early-learning-center (listed, The schools)
    fy28/public/data/early-learning-center.json  its payload: stats, grain, conclusions, sources

WHY THIS PAGE EXISTS. TJ, 7 November 2026, asked whether the ELC runs through the school
system at all, and said it is not the same thing as preschool. Both questions are answered
from documents, not from the journal alone: the journal holds only school accounts, so
finding the ELC in it cannot by itself show the ELC is a school programme (a search of a
school ledger finds only school money). The governance answer rests on the School
Committee's own minutes, the staff rosters and the payment portal, each cited.

EVERYTHING IS DERIVED. Money comes from three published datasets, every timeline entry
carries a quotation that this script FINDS in the cited document's text before writing, and
the fund's balance series is checked row by row (forward + receipts - disbursements =
carried) and year to year (each year opens on the last one's close). A quotation that is not
in its document, or a fund row that does not foot, stops the build.

WHAT IT CANNOT DO, said up front so nobody reads it in: the ELC shares fund 1312, and its
payroll account, with Extended Day. Only fees somebody typed "ELC" beside can be attributed
to it, and no spending can.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C  # noqa: E402
from conclusions import conclusion, figure, emit  # noqa: E402
import build_sitting_on_money as SOM  # noqa: E402  -- svg helpers

DATA = os.path.join(ROOT, 'sources', 'data')
OUT = os.path.join(ROOT, 'sources', 'analyses', 'early-learning-center.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'early-learning-center.json')
CHARTS = os.path.join(ROOT, 'sources', 'analyses', 'charts')
ID = 'early-learning-center'
# What each timeline tag means, in the order the legend shows them.
TAGS = [('place', 'where it was housed'), ('run', 'run by the schools'),
        ('handbook', 'handbooks'), ('rates', 'rates'), ('distinct', 'separate from preschool'),
        ('money', 'how it is paid for')]
FUND = '1312'
ELC = re.compile(r'\bELC\b|early learning', re.I)
PREK = re.compile(r'pre-?k\b|preschool|pre-school', re.I)

# THE TIMELINE. Each entry: date, which body, what the document records (our words), the
# document's text file, and a quotation from it. The quotation is matched against the text
# with whitespace collapsed; one that is not found stops the build (rule 13: quote the
# source, never your rendering of it). `tag` groups entries for the conclusions.
TIMELINE = [
    ('FY2012', 'Annual town report', 'The earliest mention we hold: a staff post named for '
     'the ELC, and the programme housed at the T.C. Passios building.',
     'town-annual-reports/text/4118-fy-2012-annual-town-report.txt',
     "The district's Extended Day, Early Learning, and School Linked Services programs "
     'operate in the building', 'place'),
    ('2018-11-07', 'Select Board', 'The Superintendent lists the ELC and Extended Day among '
     'the district’s programmes while discussing space for Pre-K classrooms.',
     'meetings/text/select-board/2018-11-07-minutes-5125.txt',
     'We have the Early Learning Center and Extended Day Program.', 'run'),
    ('2019-05-07', 'Select Board', 'The Town Manager reports the ELC will move to T.C. '
     'Passios, and distinguishes it from the integrated preschool.',
     'meetings/text/select-board/2019-05-07-minutes-5159.txt',
     'the Early Learning Program (not the integrated preschool program) relocating to the TC '
     'Passios beginning next school year', 'distinct'),
    ('2021-10-20', 'School Committee agenda, filed under advisory councils', 'A proposed '
     'Extended Day and ELC rate increase is on the agenda.',
     'meetings/text/school-advisory-councils-committees/2021-10-20-agenda-4386.txt',
     'Extended Day/ELC Proposed Rate Increase', 'rates'),
    ('2022-03-16', 'School Committee (agenda)', 'Extended Day and ELC recommendations and '
     'handbooks are on the agenda.', 'meetings/text/school-committee/2022-03-16-agenda-4452.txt',
     'Extended Day & ELC Recommendations and Handbooks', 'handbook'),
    ('2022-05-16', 'Municipal Building Design Committee', 'The teen center is ruled out as a '
     'home for the ELC because of its play equipment.',
     'meetings/text/lunenburg-municipal-building-design-committee/2022-05-16-minutes-3097.txt',
     'The teen center could not accommodate with the early learning center', 'place'),
    ('2022-12-20', 'Select Board', 'The School Committee asks for the Brooks House as an ELC; '
     'the design committee expects the programmes to return to school buildings.',
     'meetings/text/select-board/2022-12-20-minutes-5299.txt',
     'they would like to use the Brooks House as an Early Learning Center', 'place'),
    ('2023-03-01', 'School Committee (agenda)', 'Extended Day and ELC handbooks are on the '
     'agenda for action.', 'meetings/text/school-committee/2023-03-01-agenda-215.txt',
     'Extended Day & ELC Handbooks', 'handbook'),
    ('2024-02-28', 'School Committee', 'Pre-K registration and ELC registration open on '
     'different dates, as separate programmes.',
     'meetings/text/school-committee/2024-02-28-minutes-6439.txt',
     'the Early Learning Center registration will open on Monday May 20th', 'distinct'),
    ('2024-05-01', 'School Committee', 'The Director presents the Extended Day and ELC '
     'handbooks: no price or policy changes.',
     'meetings/text/school-committee/2024-05-01-minutes-6554.txt',
     'There are no price or policy changes.', 'handbook'),
    ('2025-03-19', 'School Committee', 'The FY2026 handbooks move the ELC to the Primary '
     'School.', 'meetings/text/school-committee/2025-03-19-minutes-7111.txt',
     'Early Learning Center will be moved to the Primary School.', 'handbook'),
    ('2025-03-19', 'School Committee', 'The committee adopts the unaffiliated salary '
     'schedule, described as mostly Extended Day and ELC staff paid from the revolving fund.',
     'meetings/text/school-committee/2025-03-19-minutes-7111.txt',
     'This mostly is the staff of the extended day, ELC staff and is primarily paid out of '
     'the revolving account', 'money'),
    ('2025-09-03', 'School Committee', 'The Primary School reports its enrolment as not '
     'including the ELC.', 'meetings/text/school-committee/2025-09-03-minutes-7385.txt',
     'students at the Primary School, not including the ELC', 'distinct'),
    ('2025-11-20', 'Library Board of Trustees', 'The library’s preschool storytime loses the '
     'ELC children after the move.',
     'meetings/text/library-board-of-trustees/2025-11-20-minutes-7518.txt',
     'losing the early learning center kids due to their relocation', 'place'),
    ('2026-03-18', 'School Committee', 'The FY2027 Extended Day and ELC handbooks are '
     'approved; the ELC stays at the Primary School.',
     'meetings/text/school-committee/2026-03-18-minutes-7719.txt',
     'FY 27 Extended Day and ELC Handbooks', 'handbook'),
    ('2026-09-09', 'School Committee', 'Preschool and ELC children start together, the week '
     'after kindergarten.', 'meetings/text/school-committee/2026-09-09-minutes-8002.txt',
     'preschool and Early Learning Center students began the following week', 'distinct'),
]

GAPS = ('How much of the Extended Day Revolving Fund is the Early Learning Center',
        'What the six fees the district’s payment portal sells actually cost',
        'What a fee-funded school programme costs that is not booked to its own fund')


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def read_csv(name):
    with open(os.path.join(DATA, name), encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def cite_url(rel):
    """The citable address of a text file's document: the town's URL where it has one,
    and always our copy under /docs."""
    if rel.startswith('meetings/text/'):
        stem = rel[len('meetings/text/'):].rsplit('.', 1)[0]
        with open(os.path.join(ROOT, 'sources', 'meetings', 'index.csv'), encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                if r['path'] and r['path'].rsplit('.', 1)[0] == stem:
                    return r['url'] or '/docs/meetings/' + r['path'], '/docs/meetings/' + r['path']
        raise SystemExit('early-learning-center: %s is not in the meetings index' % rel)
    if rel.startswith('town-annual-reports/text/'):
        name = os.path.basename(rel).rsplit('.', 1)[0]
        with open(os.path.join(ROOT, 'sources', 'town-annual-reports', 'index.csv'),
                  encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                if os.path.basename(r['local']).rsplit('.', 1)[0] == name:
                    ours = '/docs/town-annual-reports/docs/' + os.path.basename(r['local'])
                    return r['upstream'].split()[0], ours
        raise SystemExit('early-learning-center: %s is not in the annual reports index' % rel)
    raise SystemExit('early-learning-center: no citation rule for %s' % rel)


def facts():
    f = {}
    # -- the timeline, every quotation found in its document --------------------------
    events, missing = [], []
    for date, body, what, rel, quote, tag in TIMELINE:
        text = norm(open(os.path.join(ROOT, 'sources', rel), encoding='utf-8',
                         errors='ignore').read())
        if norm(quote) not in text:
            missing.append('%s %s: %r' % (date, rel, quote))
            continue
        url, ours = cite_url(rel)
        events.append(dict(date=date, body=body, what=what, quote=quote, tag=tag,
                           url=url, ours=ours))
    if missing:
        raise SystemExit('early-learning-center: quotations not found in their documents:\n  '
                         + '\n  '.join(missing))
    f['events'] = events
    f['handbook_years'] = sorted({e['date'][:4] for e in events if e['tag'] == 'handbook'})
    hy = [int(y) for y in f['handbook_years']]
    if any(b != a + 1 for a, b in zip(hy, hy[1:])):
        raise SystemExit('early-learning-center: handbook years are not consecutive; the '
                         'claim says "springs running"')

    # -- every document in the archive that names the ELC -------------------------------
    hits = []
    for base in ('meetings/text', 'town-annual-reports/text'):
        for dp, _, fs in os.walk(os.path.join(ROOT, 'sources', base)):
            for n in fs:
                if n.endswith('.txt'):
                    p = os.path.join(dp, n)
                    if ELC.search(open(p, encoding='utf-8', errors='ignore').read()):
                        hits.append(os.path.relpath(p, os.path.join(ROOT, 'sources')))
    f['doc_hits'] = sorted(hits)

    # -- the journal: lines typed ELC, and the fund they post to ------------------------
    rows = read_csv('munis-school-journal.csv')
    elc_lines = [r for r in rows if r['posts_to'] == 'actual'
                 and ELC.search((r['description'] or '') + ' ' + (r['comment'] or ''))]
    prek_lines = [r for r in rows if r['posts_to'] == 'actual'
                  and PREK.search((r['description'] or '') + ' ' + (r['comment'] or ''))
                  and not ELC.search(r['description'] or '')]
    f['prek_lines'] = len(prek_lines)
    by_fund = defaultdict(lambda: [0, 0.0])
    for r in elc_lines:
        k = (r['fund'], r['fund_name'], r['account_description'])
        by_fund[k][0] += 1
        by_fund[k][1] += float(r['amount'])
    f['elc_by_fund'] = sorted(by_fund.items(), key=lambda kv: kv[1][1])
    fees = defaultdict(lambda: {'elc': 0.0, 'all': 0.0, 'elc_lines': 0, 'all_lines': 0,
                                'revtrak': 0})
    for r in rows:
        if r['fund'] == FUND and r['object'].startswith('4') and r['posts_to'] == 'actual':
            y = int(r['fiscal_year'])
            amt = -float(r['amount'])
            fees[y]['all'] += amt
            fees[y]['all_lines'] += 1
            if 'REVTR' in (r['description'] + r['comment']).upper():
                fees[y]['revtrak'] += 1
            if ELC.search(r['description'] + ' ' + r['comment']):
                fees[y]['elc'] += amt
                fees[y]['elc_lines'] += 1
    f['fees'] = dict(sorted(fees.items()))
    f['journal_years'] = sorted(fees)
    if not f['journal_years']:
        raise SystemExit('early-learning-center: no fee lines found for fund %s' % FUND)

    # spending in the fund, by account, from the journal
    spend = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if r['fund'] == FUND and r['object'].startswith('5') and r['posts_to'] == 'actual':
            spend[int(r['fiscal_year'])][r['account_description']] += float(r['amount'])
    f['spend'] = {y: dict(v) for y, v in sorted(spend.items())}

    # -- the fund's year-by-year balance --------------------------------------------------
    series = {}
    for r in read_csv('special-revenue-funds.csv'):
        name = r['fund'].lower()
        if not ('extended day' in name or 'exten day' in name):
            continue
        vals = [r['v%d' % i] for i in range(1, 5)]
        if not all(v.strip() for v in vals):
            continue
        fwd, rec, dis, car = (float(v.replace(',', '')) for v in vals)
        if abs(fwd + rec - dis - car) > 0.005:
            raise SystemExit('early-learning-center: FY%s Extended Day row does not foot' % r['fy'])
        series[int(r['fy'])] = dict(fwd=fwd, rec=rec, dis=dis, car=car,
                                    src='annual town report, %s, p%s' % (r['edition'], r['page']))
    flows = [r for r in read_csv('school-fund-flows.csv') if r['fund'] == FUND]
    if not flows:
        raise SystemExit('early-learning-center: fund %s is not in school-fund-flows.csv' % FUND)
    f['overlap'] = []
    for r in flows:
        y = int(r['fiscal_year'])
        row = dict(fwd=float(r['opening_balance']), rec=float(r['received_outside']),
                   dis=float(r['spent_actual']), car=float(r['closing_balance']),
                   src='school journal (school-fund-flows.csv)')
        if y in series:
            a = series[y]
            if abs(a['rec'] - row['rec']) > 0.005 or abs(a['dis'] - row['dis']) > 0.005:
                raise SystemExit('early-learning-center: FY%d annual report and journal disagree' % y)
            f['overlap'].append(y)
            continue
        series[y] = row
    yrs = sorted(series)
    breaks = []
    for a, b in zip(yrs, yrs[1:]):
        if b == a + 1 and abs(series[a]['car'] - series[b]['fwd']) > 0.005:
            raise SystemExit('early-learning-center: FY%d does not open on FY%d close' % (b, a))
        if b != a + 1:
            breaks.append((a, b))
    f['series'] = series
    f['series_breaks'] = breaks
    f['short_years'] = [y for y in yrs if series[y]['dis'] > series[y]['rec']]

    # -- people, and the payment portal ---------------------------------------------------
    # THE ROSTERS, YEAR BY YEAR. The town's own group heading has been EXTENDED DAY, EXTENDED
    # DAY PROGRAM, Extended Day/School Linked Services, Extended Day and Ext Day/ELC, and a role
    # of Day Care at T.C. Passios before any of them -- so the match is wide on purpose (TJ:
    # "they might use acronyms or are spelled differently"). Early childhood is NOT matched: in
    # these rosters it is the preschool, which this report keeps separate. CFCE is matched
    # because the Family and Community Engagement grant moves money with this fund.
    grp = re.compile(r'ext(ended|\.)?[\s-]*day|before[\s/&-]*(and|&)?[\s/-]*after|after[\s-]*school'
                     r'|early[\s-]*learning|\bE\.?L\.?C\.?\b|day[\s-]*care|latch|school[\s-]*linked'
                     r'|community[\s-]*school|\bCFCE\b', re.I)
    roster = read_csv('staff-roster-entries.csv')
    f['roster'] = [r for r in roster
                   if grp.search(' '.join((r['role_raw'], r['position'], r['grade_or_dept'])))]
    if not f['roster']:
        raise SystemExit('early-learning-center: no Extended Day or ELC rows in the rosters')
    # Every year the Primary School roster was read, and how many names it printed: a year with
    # a roster and no group is a year the town did not print one, not a page we failed to read.
    prim = defaultdict(int)
    for r in roster:
        if r['school'] == 'primary':
            prim[int(r['fy'])] += 1
    lo = min(int(r['fy']) for r in f['roster'])
    f['primary_roster'] = {y: n for y, n in prim.items() if y >= lo}
    # For each person the rosters put in these groups in two or more years: in how many of the
    # years with NO group does that year's report text name them at all, and where.
    gy = defaultdict(set)
    for r in f['roster']:
        gy[r['name']].add(int(r['fy']))
    gap = sorted(set(f['primary_roster']) - {int(r['fy']) for r in f['roster']})
    text_of = {}
    with open(os.path.join(ROOT, 'sources', 'town-annual-reports', 'index.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            m = re.search(r'fy-(\d{4})', r['local'])
            if m and r['text'] and int(m.group(1)) in gap:
                t = open(os.path.join(ROOT, r['text']), encoding='utf-8', errors='ignore').read()
                text_of[int(m.group(1))] = text_of.get(int(m.group(1)), '') + norm(t)
    missing_text = [y for y in gap if y not in text_of]
    if missing_text:
        raise SystemExit('early-learning-center: no report text for %s' % missing_text)
    f['gap_names'] = []
    for n, ys in sorted(gy.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(ys) < 2:
            continue
        first, last = n.split()[0], n.split()[-1]
        # as the rosters print it (First Last, or Last, First) and as the wage lists do (LAST FIRST)
        pat = re.compile(r'\b(%s\s+%s|%s,?\s+%s)\b' % ((re.escape(first), re.escape(last)) * 2
                                                        if False else (re.escape(first), re.escape(last),
                                                                       re.escape(last), re.escape(first))), re.I)
        found = [y for y in gap if pat.search(text_of[y])]
        f['gap_names'].append((n, len(ys), found))
    f['directory'] = sorted({r[list(r)[7]] for r in read_csv('school-staff-directory.csv')
                             if ELC.search(','.join(r.values()))})
    f['rate'] = [r for r in read_csv('rate-register.csv') if 'ELC' in ','.join(r.values())]

    gaps = read_csv('money-gaps.csv')
    # The fund's own page on this site, read off the index the fund pages are built from,
    # by the programme name school-fund-flows.csv gives the fund. Never typed.
    prog = {r['program'] for r in flows}
    ix = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'fy-breakdown', 'index.json'),
                        encoding='utf-8'))
    pages = ['/school-funds/' + x['slug'] for x in ix['funds'] if x['name'] in prog]
    if len(pages) != 1:
        raise SystemExit('early-learning-center: expected one fund page for %s, found %r'
                         % (sorted(prog), pages))
    f['fund_page'] = pages[0]
    f['gaps'] = []
    for want in GAPS:
        g = [x for x in gaps if x['what'].startswith(want)]
        if not g:
            raise SystemExit('early-learning-center: money-gaps.csv has no row %r' % want)
        f['gaps'].append(g[0])
    return f


def payload(f):
    last = f['journal_years'][-1]
    fe = f['fees'][last]
    s = f['series']
    sy = sorted(s)
    close = s[last]['car']
    short = [y for y in f['short_years'] if y >= f['journal_years'][0]]
    usd = C.usd
    N = lambda v, unit: figure(v, C.num(v), unit)  # noqa: E731
    share = 100 * fe['elc'] / fe['all']  # C.pct takes a percentage, not a fraction
    rows = [
        conclusion(
            id='elc-fees-share',
            claim='Fees typed “ELC” came to %s in %s, of the fund’s %s in fees.'
                  % (usd(fe['elc']), C.fy(last), usd(fe['all'])),
            so_what='That is a floor for the ELC’s fees, not its total: the label is optional.',
            figures={'e': figure(fe['elc'], usd(fe['elc'])),
                     'a': figure(fe['all'], usd(fe['all'])),
                     'y': figure(last, C.fy(last)),
                     'p': figure(share, C.pct(share)),
                     'n': N(fe['elc_lines'], 'deposit lines'),
                     'm': N(fe['all_lines'], 'deposit lines')},
            figure='e', kind='measured', bearing='sizes',
            detail='%s of %s fee deposit lines in %s say ELC, %s of the fund’s fees. A deposit '
                   'batches many families’ payments, and nothing requires the label.'
                   % (C.num(fe['elc_lines']), C.num(fe['all_lines']), C.fy(last), C.pct(share)),
            basis='munis-school-journal.csv, fund 1312, revenue lines whose description or '
                  'comment contains ELC.',
            not_shown='How many children, or what the ELC charges: neither is in the ledger, '
                      'and the portal publishes no rates.'),
        conclusion(
            id='fund-spent-more-than-fees',
            claim='The fund that pays ELC staff spent more than it took in, %s of %s years.'
                  % (C.num(len(short)), C.num(len(f['journal_years']))),
            so_what='By our reckoning it closed %s at %s, which leaves nothing in reserve.'
                    % (C.fy(last), usd(close)),
            figures={'k': N(len(short), 'years'), 'n': N(len(f['journal_years']), 'years'),
                     'y': figure(last, C.fy(last)), 'c': figure(close, usd(close)),
                     'r': figure(s[last]['rec'], usd(s[last]['rec'])),
                     'd': figure(s[last]['dis'], usd(s[last]['dis']))},
            figure='c', kind='measured', bearing='sizes',
            detail='In %s fees were %s and spending %s. The closing balance is carried '
                   'forward by us from the ledger; the town has not printed it.'
                   % (C.fy(last), usd(s[last]['rec']), usd(s[last]['dis'])),
            basis='school-fund-flows.csv (fund 1312), which ties every year to the Town’s '
                  'period-13 report; the opening balance is the annual report’s.',
            not_shown='How much of the spending is the ELC and how much Extended Day: they '
                      'share one payroll account.'),
        conclusion(
            id='run-by-the-schools',
            claim='The ELC handbook came to the School Committee in %s springs running.'
                  % C.num(len(f['handbook_years'])),
            so_what='The ELC is a school district programme, run separately from the preschool.',
            figures={'h': N(len(f['handbook_years']), 'years')},
            figure='h', kind='measured', bearing='lever',
            detail='Its director is district staff, its fees go to a school revolving fund, '
                   'and it registers on its own dates, apart from Pre-K.',
            basis='School Committee agendas and minutes, the staff directory and the '
                  'journal; each quoted in the timeline.',
            not_shown='Whether the ELC is licensed as child care, or its age range: no '
                      'document we hold says.'),
    ]
    return {
        'id': 'early-learning-center',
        'title': 'The Early Learning Center',
        'grain': 'Dollars in the school Extended Day Revolving Fund (fund 1312), which pays '
                 'for the ELC and Extended Day together, and dated documents that name the ELC.',
        'stats': [
            {'value': usd(fe['elc']), 'label': 'fees typed “ELC”, %s' % C.fy(last)},
            {'value': usd(fe['all']), 'label': 'all fees into the fund, %s' % C.fy(last)},
            {'value': usd(close), 'label': 'fund balance at the %s close (ours)' % C.fy(last)},
            {'value': C.num(len(f['doc_hits'])), 'label': 'documents that name the ELC'},
        ],
        'conclusions': emit('early-learning-center', rows),
        'sources': [
            {'what': 'The Extended Day Revolving Fund’s own page: every posting, by year',
             'where': f['fund_page']},
            {'what': 'Every school journal line, FY2023 to FY2026',
             'where': '/docs/data/munis-school-journal.csv'},
            {'what': 'The fund’s money in, out and balance, by year, from the journal',
             'where': '/docs/data/school-fund-flows.csv'},
            {'what': 'The fund’s balance from the annual town reports',
             'where': '/docs/data/special-revenue-funds.csv'},
            {'what': 'Staff rosters from the annual reports',
             'where': '/docs/data/staff-roster-entries.csv'},
            {'what': 'Meeting minutes and agendas (each cited in the timeline)',
             'where': '/minutes/find/'},
        ],
        'timeline': [dict(date=e['date'], body=e['body'], what=e['what'], tag=e['tag'],
                          url=e['url']) for e in f['events']],
        'timeline_tags': [dict(tag=t, label=l) for t, l in TAGS],
        'fund_series': [dict(fy=y, opening=round(s[y]['fwd'], 2), received=round(s[y]['rec'], 2),
                             spent=round(s[y]['dis'], 2), closing=round(s[y]['car'], 2),
                             source=s[y]['src']) for y in sy],
        'fees_by_year': [dict(fy=y, elc=round(f['fees'][y]['elc'], 2),
                              rest=round(f['fees'][y]['all'] - f['fees'][y]['elc'], 2),
                              all=round(f['fees'][y]['all'], 2))
                         for y in f['journal_years']],
        'not_established': [
            'How many children attend the ELC, in any year. No document we hold counts them; '
            'the Primary School reports its enrolment without them.',
            'What the ELC charges. The payment portal sells it beside Extended Day and '
            'publishes no rates, and no fee schedule is in a budget book or a warrant.',
            'What the ELC costs. It shares fund 1312, and its payroll account, with Extended '
            'Day, so its spending cannot be separated.',
            'Whether the general fund carries any ELC cost, such as space, utilities or '
            'administration, that is not booked to the fund.',
            'Its age range, hours, or whether it is licensed as child care.',
        ],
    }


def render(f, pay):
    L = []
    w = L.append
    usd = C.usd
    s = f['series']
    sy = sorted(s)
    jy = f['journal_years']
    w('# The Early Learning Center')
    w('')
    w('A school district programme, run beside Extended Day and paid for from the same fees, '
      'and not the same thing as the preschool.')
    w('')
    w('![Every dated document that names the ELC, %s to %s, marked by what it records.](charts/%s-timeline.svg)'
      % (f['events'][0]['date'][:4] if f['events'][0]['date'][0].isdigit() else f['events'][0]['date'],
         f['events'][-1]['date'][:4], ID))
    w('')
    w('## What the documents establish')
    w('')
    w('- **The schools run it.** The Extended Day and ELC handbooks come to the School '
      'Committee each spring (%s), and the staff directory lists the post that runs it as '
      '*%s*.' % (', '.join(f['handbook_years']), '; '.join(f['directory'])))
    w('- **It is not the preschool.** The Town Manager called it *“the Early Learning Program '
      '(not the integrated preschool program)”* in 2019; it registers on its own dates, apart '
      'from Pre-K; the Primary School counts its enrolment *“not including the ELC”*; and the '
      'payment portal sells *Extended Day & ELC* and a *Primary Preschool Program* as two items.')
    w('- **Its money is a school revolving fund.** Families pay through the district’s RevTrak '
      'portal, and the deposits post to fund %s, the [Extended Day Revolving Fund](%s). The '
      'fund pays the staff of both programmes, and their health insurance, from those fees.'
      % (FUND, f['fund_page']))
    w('- **The journal alone could not have shown this**: it holds only school accounts, so '
      'anything found in it is school money by construction. The minutes are what establish it.')
    w('')
    w('## Timeline')
    w('')
    w('Every entry quotes its document, and the build fails if the quotation is not there.')
    w('')
    w('| when | body | what the document records | in its words |')
    w('|---|---|---|---|')
    for e in f['events']:
        w('| %s | %s | %s | *“%s”* ([document](%s), [our copy](%s)) |'
          % (e['date'], e['body'], e['what'], e['quote'], e['url'], e['ours']))
    w('')
    w('Two School Committee transfers from the Extended Day account to the town for rent of '
      'T.C. Passios were voted on 2019-10-02 and 2020-02-26; they are heard in the meeting '
      'recordings only, and the amounts are a caption model’s, not figures '
      '(`board-transfers.csv`).')
    w('')
    w('## The money')
    w('')
    w('Every posting to the fund, by year and by account, is on [the fund’s own page](%s).'
      % f['fund_page'])
    w('')
    w('### Fees typed “ELC”, against all fees into the fund')
    w('')
    w('| fiscal year | fees typed ELC | deposit lines | all fees into fund %s | deposit lines |'
      % FUND)
    w('|---|---:|---:|---:|---:|')
    for y in jy:
        x = f['fees'][y]
        w('| %s | %s | %s | %s | %s |' % (C.fy(y), usd(x['elc']), C.num(x['elc_lines']),
                                          usd(x['all']), C.num(x['all_lines'])))
    w('')
    w('![Fees typed ELC against the rest of the fund’s fees, by fiscal year.](charts/%s-fees.svg)' % ID)
    w('')
    w('The label is typed by whoever posts the deposit and nothing requires it, so the ELC '
      'column is a floor. The rest of the fund’s fees are Extended Day, summer and '
      'unlabelled ELC payments in proportions the ledger cannot tell apart.')
    w('')
    w('### What the fund spent, by account')
    w('')
    accts = sorted({a for y in f['spend'] for a in f['spend'][y]})
    w('| account | %s |' % ' | '.join(C.fy(y) for y in sorted(f['spend'])))
    w('|---|%s' % ('---:|' * len(f['spend'])))
    for a in accts:
        w('| %s | %s |' % (a.lower(), ' | '.join(usd(f['spend'][y].get(a, 0))
                                                for y in sorted(f['spend']))))
    w('')
    w('One payroll account carries both programmes, so none of this can be attributed to the '
      'ELC.')
    w('')
    w('### The fund, year by year')
    w('')
    w('![Fees in, spending out and the closing balance of fund %s, %s to %s.](charts/%s-fund.svg)'
      % (FUND, C.fy(sy[0]), C.fy(sy[-1]), ID))
    w('')
    w('| fiscal year | opening | fees and receipts | spent | closing | from |')
    w('|---|---:|---:|---:|---:|---|')
    for y in sy:
        r = s[y]
        w('| %s | %s | %s | %s | %s | %s |' % (C.fy(y), usd(r['fwd']), usd(r['rec']),
                                              usd(r['dis']), usd(r['car']), r['src']))
    w('')
    gaps = ', '.join('%s to %s' % (C.fy(a + 1), C.fy(b - 1)) for a, b in f['series_breaks'])
    w('Each row foots (opening + receipts - spent = closing) and each year opens on the last '
      'one’s close%s. %s is in both the annual report and the journal and they agree to the '
      'cent. The years %s are not in our reading of the annual reports’ fund tables. This is '
      'the whole fund, Extended Day included.'
      % ('' if not f['series_breaks'] else ' where the years are consecutive',
         ', '.join(C.fy(y) for y in f['overlap']), gaps or 'none'))
    w('')
    w('### Not counted here')
    w('')
    w('%s journal lines are labelled preschool or PreK. The documents treat the preschool as a '
      'separate programme, so they are left out, and so is the federal early childhood special '
      'education grant (#262), whose lines never name the ELC.' % C.num(f['prek_lines']))
    w('')
    w('### Every journal line typed “ELC”, by where it posts')
    w('')
    w('| fund | account | lines | net amount |')
    w('|---|---|---:|---:|')
    for (fund, fname, acct), (n, amt) in f['elc_by_fund']:
        w('| %s %s | %s | %s | %s |' % (fund, fname.lower(), acct.lower(), C.num(n), usd(amt)))
    w('')
    w('Revenue is negative in the ledger: a fee is a credit.')
    w('')
    w('## People')
    w('')
    w('Who the annual town reports list under Extended Day, the ELC and the programmes beside '
      'them, as the town headed them each year.')
    w('')
    w('| year | group, as printed | names (role, where printed) | page |')
    w('|---|---|---|---|')
    by_y = defaultdict(list)
    for r in f['roster']:
        by_y[int(r['fy'])].append(r)
    yrs = sorted(set(by_y) | set(f['primary_roster']))
    for y in yrs:
        rs = by_y.get(y)
        if not rs:
            w('| %s | *none printed* | the Primary School roster lists %s names and no such group | |'
              % (C.fy(y), C.num(f['primary_roster'][y])))
            continue
        groups = defaultdict(list)
        for r in rs:
            groups[(r['grade_or_dept'] or r['school']).strip()].append(r)
        for g, gr in groups.items():
            names = '; '.join('%s%s' % (r['name'], ' (%s)' % r['role_raw'].strip('() ')
                                        if r['role_raw'].strip('() ') else '') for r in gr)
            pages = ', '.join(sorted({'p%s' % r['page'] for r in gr}))
            w('| %s | %s | %s | %s |' % (C.fy(y), g, names, pages))
    w('')
    gap = [y for y in yrs if y not in by_y]
    w('In %s of these %s years the Primary School roster was printed and read but carries no '
      'Extended Day or ELC group. To check that the group was not simply filed under another '
      'name, each person listed in it in two or more years was searched for by full name, in '
      'either order, in the full text of those reports:' % (C.num(len(gap)), C.num(len(yrs))))
    w('')
    w('| name | years in the group | named anywhere in the years with no group |')
    w('|---|---:|---|')
    for n, k, found in f['gap_names']:
        w('| %s | %s | %s |' % (n, C.num(k), ', '.join(C.fy(y) for y in found) or 'none'))
    w('')
    w('Where a name does appear in a year with no group, it is under another heading, such as a '
      'classroom or the town’s wage list, which names no programme; a name found does not say '
      'what the person did that year. A roster lists names with no FTE and no funding source, '
      'so it is not a staffing level.')
    w('')
    w('## What we cannot say')
    w('')
    for n in pay['not_established']:
        w('- %s' % n)
    w('')
    w('Registered in `sources/data/money-gaps.csv`, each with the document that would settle it:')
    w('')
    for g in f['gaps']:
        w('- **%s** %s' % (g['what'], g['why']))
    w('')
    w('## Where it comes from')
    w('')
    w('| what | where |')
    w('|---|---|')
    for x in pay['sources']:
        w('| %s | %s |' % (x['what'], x['where']))
    w('')
    w('%s documents in the archive name the ELC: %s.'
      % (C.num(len(f['doc_hits'])), ', '.join('`%s`' % h for h in f['doc_hits'])))
    w('')
    return '\n'.join(L) + '\n'


INK, MUTED, GRID = SOM.INK, SOM.MUTED, SOM.GRID
TAG_COLOR = {'place': '#2b6cb0', 'run': '#7c3aed', 'handbook': '#0f766e', 'rates': '#b45309',
             'distinct': '#be185d', 'money': '#15803d'}
C_IN, C_OUT, C_BAL, C_ELC, C_REST = '#2b6cb0', '#dc2626', '#111827', '#be185d', '#94a3b8'


def usdk(v):
    a = abs(v)
    t = '$%.1fM' % (a / 1e6) if a >= 1e6 else '$%dk' % round(a / 1e3) if a >= 1e3 else '$%d' % round(a)
    return ('-' if v < 0 else '') + t


def timeline_svg(events):
    W, rh, top = 900, 34, 70
    H = top + rh * len(events) + 30
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">The Early Learning '
         'Center in the documents</text>' % INK]
    for i, (t, l) in enumerate(TAGS):
        x = 16 + i * 145
        b.append('<circle cx="%d" cy="44" r="5" fill="%s"/><text x="%d" y="48" font-size="10.5" '
                 'fill="%s">%s</text>' % (x + 5, TAG_COLOR[t], x + 14, MUTED, SOM.esc(l)))
    b.append('<line x1="110" y1="%d" x2="110" y2="%d" stroke="%s" stroke-width="2"/>'
             % (top - 8, top + rh * len(events) - 14, GRID))
    for i, e in enumerate(events):
        y = top + i * rh
        b.append('<text x="96" y="%d" font-size="11" text-anchor="end" fill="%s">%s</text>'
                 % (y + 4, MUTED, SOM.esc(e['date'])))
        b.append('<circle cx="110" cy="%d" r="6" fill="%s"/>' % (y, TAG_COLOR[e['tag']]))
        b.append('<text x="126" y="%d" font-size="11" font-weight="700" fill="%s">%s</text>'
                 % (y + 4, INK, SOM.esc(e['body'])))
        what = e['what'] if len(e['what']) <= 110 else e['what'][:107] + '...'
        b.append('<text x="126" y="%d" font-size="10.5" fill="%s">%s</text>'
                 % (y + 17, MUTED, SOM.esc(what)))
    return SOM.svg_wrap(W, H, 'The Early Learning Center in the documents', b)


def fund_svg(series):
    yrs = sorted(series)
    W, H, L, B, T = 900, 380, 70, 300, 50
    hi = max(max(series[y]['rec'], series[y]['dis'], series[y]['car']) for y in yrs)
    lo = min(0, min(series[y]['car'] for y in yrs))
    sc = (B - T) / (hi - lo)
    zero = B + lo * sc
    gw = (W - L - 20) / len(yrs)
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Extended Day Revolving '
         'Fund (ELC and Extended Day together): in, out, and the balance left</text>' % INK,
         '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s"/>' % (L, zero, W - 20, zero, GRID)]
    pts = []
    for i, y in enumerate(yrs):
        x0 = L + i * gw + 4
        bw = (gw - 12) / 2
        for j, (k, c) in enumerate((('rec', C_IN), ('dis', C_OUT))):
            h = series[y][k] * sc
            b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" opacity="0.8"/>'
                     % (x0 + j * bw, zero - h, bw, h, c))
        pts.append((x0 + bw, zero - series[y]['car'] * sc))
        b.append('<text x="%.1f" y="%d" font-size="9.5" text-anchor="middle" fill="%s">%s</text>'
                 % (x0 + bw, B + 16, MUTED, str(y)[2:]))
    for (a, c) in zip(yrs, yrs[1:]):
        if c == a + 1:
            i = yrs.index(a)
            b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>'
                     % (pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], C_BAL))
    for (x, yy) in pts:
        b.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s"/>' % (x, yy, C_BAL))
    for i, (t, c) in enumerate((('fees and receipts', C_IN), ('spent', C_OUT),
                                ('closing balance', C_BAL))):
        x = L + i * 170
        b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/><text x="%d" y="%d" '
                 'font-size="11" fill="%s">%s</text>' % (x, H - 30, c, x + 14, H - 21, INK, t))
    b.append('<text x="%d" y="%d" font-size="10" fill="%s">fiscal year (20xx); the scale runs from '
             '%s to %s; no bars where a year is not read</text>' % (L, H - 6, MUTED, usdk(lo), usdk(hi)))
    return SOM.svg_wrap(W, H, 'Extended Day Revolving Fund by year', b)


def fees_svg(fees, yrs):
    W, H, L, B, T = 900, 330, 70, 260, 50
    hi = max(fees[y]['all'] for y in yrs)
    sc = (B - T) / hi
    gw = (W - L - 20) / len(yrs)
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Fees into fund %s: '
         'deposits typed ELC, and everything else</text>' % (INK, FUND)]
    for i, y in enumerate(yrs):
        x = L + i * gw + gw * 0.2
        bw = gw * 0.6
        e, a = fees[y]['elc'], fees[y]['all']
        b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 % (x, B - a * sc, bw, (a - e) * sc, C_REST))
        b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 % (x, B - e * sc, bw, e * sc, C_ELC))
        b.append('<text x="%.1f" y="%.1f" font-size="10" text-anchor="middle" fill="%s">%s typed ELC'
                 ' of %s</text>' % (x + bw / 2, B - a * sc - 6, INK, usdk(e), usdk(a)))
        b.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">%s</text>'
                 % (x + bw / 2, B + 16, MUTED, C.fy(y)))
    for i, (t, c) in enumerate((('typed ELC', C_ELC), ('the rest of the fund’s fees', C_REST))):
        x = L + i * 170
        b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/><text x="%d" y="%d" '
                 'font-size="11" fill="%s">%s</text>' % (x, H - 30, c, x + 14, H - 21, INK, SOM.esc(t)))
    return SOM.svg_wrap(W, H, 'Fees into fund %s by year' % FUND, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    f = facts()
    pay = payload(f)
    doc = render(f, pay)
    js = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    outs = [(OUT, doc), (PAYLOAD, js),
            (os.path.join(CHARTS, ID + '-timeline.svg'), timeline_svg(f['events'])),
            (os.path.join(CHARTS, ID + '-fund.svg'), fund_svg(f['series'])),
            (os.path.join(CHARTS, ID + '-fees.svg'), fees_svg(f['fees'], f['journal_years']))]
    if a.check:
        rc = 0
        for path, want in outs:
            cur = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
            if cur != want:
                print('STALE %s' % os.path.relpath(path, ROOT))
                rc = 1
        if not rc:
            print('early learning center: page and payload current')
        return rc
    for path, text in outs:
        tmp = path + '.tmp'
        open(tmp, 'w', encoding='utf-8', newline='\n').write(text)
        os.replace(tmp, path)
    print('wrote %s' % ', '.join(os.path.relpath(p, ROOT) for p, _ in outs))
    return 0


if __name__ == '__main__':
    sys.exit(main())
