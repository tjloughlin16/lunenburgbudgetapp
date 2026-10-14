#!/usr/bin/env python3
"""Town reserves, split into topic pages: free cash and the stabilization funds.

    python3 scripts/build_town_reserves_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_town_reserves_topics.py --check   # fail if any output would change

WHAT THIS ABSORBS. /analysis/free-cash, /analysis/stabilization-funds,
/analysis/stabilization-option and the /free-cash-for-schools lever page answered eleven
questions between them, several of them twice (what the general fund holds, who may spend
it, what it buys against the gap). Each gets one page here.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD, and it refuses to write when two sources
that should agree do not:

  sources/data/free-cash-proof.csv      the Division of Local Services free cash proof,
                                        2021-2025, by the year of the 1 July certification.
  fy28/public/data/free-cash.json       build_free_cash_charts.py: composition, the Town's own
                                        undesignated fund balance roll-forward, peer multiples.
  sources/data/free-cash-history-fincom.csv
                                        the Town's Free Cash Fact Sheet (FY27 warrant packet):
                                        certified free cash by FISCAL year beside the operating
                                        budget it divides by. Asserted equal to the DLS proof
                                        where the two overlap, one year apart.
  sources/data/capital-funding-history.csv
                                        the FY27 capital plan's ten-year funding table.
  fy28/public/data/model.json           freeCash: the projection's gaps, the redirect ladder,
                                        the capital consequence. OURS -- every figure from it is
                                        an `estimate`.
  sources/data/trust-agency-balances.csv
                                        the town's MUNIS trust and agency report at 31 March
                                        2026: each account's opening balance, money in, money
                                        out and what remains.
  sources/data/stabilization-balances.csv, fy28/public/data/stabilization-funds.json
                                        the general fund's year-end series, proven on the trust
                                        table's own identities.
  sources/data/town-meeting-votes.csv, sources/data/stabilization-flows.csv
                                        deposits and withdrawals, as Town Meeting voted them.
  fy28/public/data/stabilization-option.json
                                        the burndown, recomputed here and asserted equal.

THREE THINGS THE OLD PAGES GOT WRONG -- all three now fixed at the source, 13 October 2026:

  * build_stabilization.flows() classified articles by subject and never read the RESULT, so
    its deposit total included an article that was PASSED OVER (FY2012, $277,432) and its
    "voted back out" figure the $986,000 article Town Meeting DEFEATED 29-92. flows() now
    files anything that did not pass under `not_passed`, and the FY2019 "$08,222." amount
    under `garbled`; this file reads both buckets rather than re-deriving them.
  * town-meeting-votes.csv had no row for the May 2024 annual meeting's articles 8-13, which
    the FY2024 annual report prints on pages 144-145. The rows are now in the CSV, quoted
    verbatim and passing extract_town_meeting_votes.py --check. The fallback below still reads
    articles 12 and 13 off the report, asserted verbatim, if the CSV ever loses them again.
  * $3,147,178.96 is the general fund's OPENING balance on 1 July 2025 (the ledger's
    `beginning`), not its balance at 31 March 2026, which is $3,244,478.12. Labelled as such.

RULE 13a. The Town's fact sheet and capital plan are documents people assembled; the DLS proof
is the state's calculation from the Town's balance sheet; the MUNIS report is the books. Where
two describe the same money (certified, identified, undesignated) they are shown side by side
and never reconciled into one.

RULE 11. Free cash is a town-wide balance. Nothing published attributes it to a department,
and nothing here does.
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import build_stabilization as BS  # noqa: E402  (read-only: its article classifier)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(D, 'archive-manifest.csv')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
AR = os.path.join(ROOT, 'sources', 'town-annual-reports', 'text')

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home in ('free-cash', 'town-reserves') and gen == 'build_town_reserves_topics.py']


def fail(msg):
    raise SystemExit('build_town_reserves_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def rows(name):
    return list(csv.DictReader(open(os.path.join(D, name), encoding='utf-8')))


def usd2(x):
    x = float(x)
    return ('-$' if x < 0 else '$') + format(abs(x), ',.2f')


def norm(s):
    return ' '.join((s or '').split())


def said_file(rel, quote, board, kind='minutes'):
    """A quotation asserted here, verbatim, against our copy of the minutes."""
    text = norm(open(os.path.join(MINUTES, rel), encoding='utf-8').read())
    if norm(quote) not in text:
        fail('quote is not verbatim in %s: %r' % (rel, quote))
    date = re.search(r'(\d{4}-\d{2}-\d{2})', rel).group(1)
    return dict(quote=quote, board=board, date=date, href='/docs/minutes/text/' + rel,
                label='%s %s, %s' % (board, kind, date))


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    town = 'Town of Lunenburg'
    spec = {
        'dls': ('state-dls/free-cash-proof-lunenburg.xlsx',
                'Massachusetts Division of Local Services, Free Cash Proof'),
        'sheet': ('budget-workbooks/finance-committee/fy27-budget/tm-warrant/'
                  'free-cash-fact-sheet.docx', town + ' — Free Cash Fact Sheet, FY27 warrant'),
        'release': ('town-budget/docs/4090-click-here-for-a-release-on-quot-understanding-'
                    'lunenburg-apos-s-fy27-budget-how-.pdf', town + ' — FY27 budget release'),
        'ar25': ('town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf',
                 town + ' — annual town report'),
        'ar24': ('town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf',
                 town + ' — annual town report'),
        'ar23': ('town-annual-reports/docs/4131-fy-2023-annual-town-report.pdf',
                 town + ' — annual town report'),
        'capplan': ('town-budget/docs/4111-article-13-fy-2027-capital-plan.pdf',
                    town + ' — FY2027 capital plan'),
        'trust': ('town-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx',
                  town + ' — Town Accountant (MUNIS)'),
        'fcplan': ('budget-workbooks/finance-committee/fy26-budget/'
                   'free-cash-appropriations-updated-2.27.25.xlsx',
                   town + ' — Finance Committee free cash plan'),
    }
    out = {}
    for k, (key, pub) in spec.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key)
    ours = {
        'd-proof': ('free-cash-proof.csv', 'the DLS proof, line by line, nine towns'),
        'd-sheet': ('free-cash-history-fincom.csv', 'the Town’s free cash history table'),
        'd-cap': ('capital-funding-history.csv', 'the capital plan’s funding table'),
        'd-trust': ('trust-agency-balances.csv', 'the MUNIS trust and agency report'),
        'd-stab': ('stabilization-balances.csv', 'year-end balances, each proven'),
        'd-flows': ('stabilization-flows.csv', 'withdrawals read out of article text'),
        'd-votes': ('town-meeting-votes.csv', 'every Town Meeting article, quoted'),
        'd-fcplan': ('free-cash-fy26.csv', 'the free cash plan for the May 2025 meeting'),
    }
    for k, (f, what) in ours.items():
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    out['model'] = dict(label='Lunenburg Budget Project — model.json (the projection; ours)',
                        href='/data/model.json')
    return out


# --------------------------------------------------------------------- the data

def dls_lunenburg():
    """Certified and identified free cash for Lunenburg, by certification year."""
    out = {}
    for r in rows('free-cash-proof.csv'):
        if r['town'] != 'Lunenburg':
            continue
        y = int(r['year'])
        if r['line'] == 'Current Year Calculation':
            out.setdefault(y, {})['certified'] = float(r['amount'])
    if sorted(out) != [2021, 2022, 2023, 2024, 2025]:
        fail('the DLS proof no longer holds Lunenburg 2021-2025: %s' % sorted(out))
    return out


def fact_sheet():
    out = {}
    for r in rows('free-cash-history-fincom.csv'):
        fy = int(r['fiscal_year'])
        cert, base = float(r['certified_free_cash']), float(r['prior_year_operating_budget'])
        printed = float(r['pct_of_budget'].rstrip('%'))
        if abs(round(100 * cert / base, 2) - printed) > 0.005:
            fail('FY%d: the fact sheet prints %.2f%% and its own figures give %.2f%%'
                 % (fy, printed, 100 * cert / base))
        out[fy] = dict(certified=cert, base=base, pct=printed, date=r['date_certified'])
    return out


def deposits():
    """Deposits into the two funds Town Meeting controls for general use and for capital --
    the general Stabilization Fund and the Special Purpose (vehicles and equipment) fund --
    counted only where the vote PASSED. Returns (rows, garbled)."""
    fl = BS.flows()
    keep = ('Stabilization Fund (general)', 'Special Purpose Stabilization')
    quotes = {}
    for r in rows('town-meeting-votes.csv'):
        quotes[(int(r['fy']), r['meeting'], r['article'])] = norm(r['quote'])
    out = []
    # FY2019 special article 2 prints "$08,222." -- a digit is missing from the page's own
    # text layer. flows() sets it aside as `garbled`; it is shown here by name, never summed.
    garbled = [dict(d, quote=quotes[(d['fy'], d['meeting'], d['article'])])
               for d in fl['garbled'] if d['fund'] in keep]
    for d in fl['deposits']:
        if d['fund'] not in keep or d['result'] not in BS.PASSED:
            continue
        q = quotes[(d['fy'], d['meeting'], d['article'])]
        out.append(dict(fy=d['fy'], meeting=d['meeting'], article=d['article'],
                        fund='general' if d['fund'].endswith('(general)') else 'special',
                        amount=d['amount'], free_cash='free cash' in q.lower(), quote=q,
                        source='town-meeting-votes.csv'))
    # Rule 13c: the May 2024 annual meeting's two deposits are printed in the FY2024 annual
    # report and missing from the extract. Read them off the page, verbatim, while it lacks them.
    text = norm(open(os.path.join(AR, '4132-fy-2024-annual-town-report.txt'),
                     encoding='utf-8').read())
    for art, fund, amt, words in (
            ('12', 'general', 100000.0,
             'transfer from Free Cash the sum of $100,000 to the Stabilization Fund.'),
            ('13', 'special', 250000.0,
             'transfer from Free Cash the sum of $250,000 to the Special Pur- pose '
             'Stabilization Fund.')):
        if any(r['fy'] == 2024 and r['fund'] == fund for r in out):
            continue
        i = text.find('ARTICLE %s. To see if the Town will vote to raise and appropriate or '
                      'transfer from available funds, a sum of money to the' % art)
        j = text.find('ARTICLE %d.' % (int(art) + 1), i)
        if i < 0 or j < 0 or words not in text[i:j]:
            fail('the FY2024 report no longer prints article %s as %r' % (art, words))
        out.append(dict(fy=2024, meeting='annual', article=art, fund=fund, amount=amt,
                        free_cash=True, quote=words, source='4132-fy-2024-annual-town-report'))
    if len(garbled) != 1:
        fail('expected one garbled deposit amount, found %d' % len(garbled))
    passed_over = [u for u in fl['not_passed'] if u['fy'] == 2025 and u['fund'] in keep]
    if sorted(u['result'] for u in passed_over) != ['passed_over', 'passed_over']:
        fail('the May 2025 stabilization articles are no longer both passed over')
    return sorted(out, key=lambda r: (r['fy'], r['fund'])), garbled[0], fl


def withdrawals(fl):
    """Every withdrawal this archive can read that PASSED: the clauses the annual reports
    print inside other articles (confidence `clear`), and the articles that are withdrawals."""
    out = [dict(fy=int(r['fy']), fund=r['fund'], amount=float(r['amount']), what='clause',
                document=r['document'])
           for r in rows('stabilization-flows.csv')
           if r['direction'] == 'out' and r['confidence'] == 'clear']
    for s in fl['spends']:
        if s['result'] == 'passed':
            out.append(dict(fy=s['fy'], fund=s['fund'], amount=s['amount'], what='article',
                            document='town-meeting-votes.csv'))
    # Defeated draws are in flows()'s `not_passed`, not among the spends. Only a PRICED
    # draw OUT of a fund counts as a failed withdrawal here.
    failed = [s for s in fl['not_passed']
              if s['amount'] is not None and BS.SPEND.search(s['subject'])]
    return sorted(out, key=lambda r: (-r['fy'], -r['amount'])), failed


# --------------------------------------------------------------------- the pages

def build():
    FCJ = load('free-cash.json')
    SF = load('stabilization-funds.json')
    SO = load('stabilization-option.json')
    M = load('model.json')['freeCash']
    src = sources()
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    Y = lambda v: figure(v, str(v), 'certification year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    # ------------------------------------------------ free cash: the series
    dls = dls_lunenburg()
    comp = {c['year']: c for c in FCJ['composition']}
    for y in dls:
        if abs(dls[y]['certified'] - comp[y]['certified']) > 0.5:
            fail('%d certified: proof %.0f, free-cash.json %.0f' % (y, dls[y]['certified'],
                                                                    comp[y]['certified']))
    sheet = fact_sheet()
    # The two publishers label the same money one year apart. Proved, not assumed.
    for y in dls:
        if abs(sheet[y + 1]['certified'] - dls[y]['certified']) > 0.5:
            fail('the fact sheet’s FY%d does not equal the DLS %d certification' % (y + 1, y))
    c25, c24, c23 = (comp[y]['certified'] for y in (2025, 2024, 2023))
    if not (c23 < c24 < c25 and c25 == max(s['certified'] for s in sheet.values())):
        fail('2025 is no longer the highest certification, or 2023-2025 no longer rise')
    low = min(dls, key=lambda y: dls[y]['certified'])
    if low != 2023:
        fail('the lowest certification of 2021-2025 is no longer 2023')
    i25 = comp[2025]['identified']
    vd = {v['year']: v for v in FCJ['versus_dls']}
    ufb25 = vd[2025]['undesignated']
    if abs(vd[2025]['certified'] - c25) > 0.5 or abs(vd[2025]['identified'] - i25) > 0.5:
        fail('free-cash.json versus_dls no longer matches the proof for 2025')
    differ = FCJ['crossfoot']['certified_differs']
    tested = FCJ['crossfoot']['tested']

    fx = {}
    fx['cert25'] = f('cert25', U(c25), 'free cash certified as of 1 July 2025 (state)',
                     'published', allow=('1 July 2025',))
    fx['ident25'] = f('ident25', U(i25), 'free cash the same proof identifies, July 2025',
                      'published', allow=('July 2025',))
    fx['ufb25'] = f('ufb25', U(ufb25), 'the Town’s own undesignated fund balance, 30 June 2025',
                    'published', allow=('30 June 2025',))
    fx['cert24'] = f('cert24', U(c24), 'certified as of 1 July 2024', 'published',
                     allow=('1 July 2024',))
    fx['cert23'] = f('cert23', U(c23), 'as of 1 July 2023, the low of five years', 'published',
                     allow=('1 July 2023',))
    fs16 = sheet[2016]['certified']
    fx['fs16'] = f('fs16', U(fs16), 'certified for %s, the Town’s fact sheet' % C.fy(2016),
                   'published', {'y': F(2016)})
    fx['why-differ'] = f('why-differ', None, 'why the state certifies less than it identifies',
                         'gap', closes='DLS’s free cash certification letter to the Town, '
                                       'stating its adjustments to the submitted balance sheet')
    dls_rows = [dict(label=str(y), cells=[C.usd(comp[y]['identified']), C.usd(comp[y]['certified']),
                                          C.fy(y + 1)]) for y in sorted(dls, reverse=True)]
    sheet_rows = [dict(label=C.fy(fy), cells=[C.usd(s['certified']), C.usd(s['base']),
                                              C.pct(s['pct'], 2)])
                  for fy, s in sorted(sheet.items(), reverse=True)]
    # The signature of the balance topic AND of the Free cash hub: one chart, two pages.
    fc_chart = TP.series(
        'Certified free cash by year', [C.fy(fy) for fy in sorted(sheet)],
        [TP.track('The state’s proof', [dls[fy - 1]['certified'] if fy - 1 in dls else None
                                        for fy in sorted(sheet)], 'published', 'bar'),
         TP.track('The Town’s fact sheet only', [None if fy - 1 in dls else
                                                 sheet[fy]['certified']
                                                 for fy in sorted(sheet)], 'stated', 'bar')],
        '$', kind='bar', stacked=True,
        note='By the fiscal year the money can be spent in. Where both publish a year, '
             'they agree to the dollar.')
    out['free-cash-balance'] = TP.page(
        'free-cash-balance',
        'The state certified %s of free cash as of 1 July 2025, the most in any year the '
        'Town’s records list.' % C.usd(c25),
        [fx['cert25'], fx['cert24'], fx['cert23'], fx['fs16'], fx['ident25'], fx['ufb25'],
         fx['why-differ']],
        [con('Free cash fell to %s in July %s and has risen each year since, to %s in July %s.'
             % (C.usd(c23), '2023', C.usd(c25), '2025'),
             ['cert23', 'cert24', 'cert25'],
             {'a': U(c23), 'y': Y(2023), 'b': U(c25), 'z': Y(2025)}),
         con('One close, three published figures: %s certified, %s identified, %s '
             'undesignated.' % (C.usd(c25), C.usd(i25), C.usd(ufb25)),
             ['cert25', 'ident25', 'ufb25', 'why-differ'],
             {'a': U(c25), 'b': U(i25), 'c': U(ufb25)},
             notes=[step('The certified figure differs from the identified one in %s of %s '
                         'town-years of the proof, and the workbook prints no line '
                         'reconciling them.' % (C.num(differ), C.num(tested)), 'gap',
                         {'n': N(differ), 'm': N(tested)},
                         closes='DLS’s certification letter to the Town')]),
         con('The state labels free cash by its 1 July balance; the Town by the year it can be '
             'spent, one later.', ['cert25', 'fs16'], allow=('1 July',),
             notes=[step('Checked, not assumed: each of the Town’s fiscal-year figures equals '
                         'the state’s certification for the year before, in all %s years the '
                         'two share.' % 'five', 'measured')])],
        # The signature: the record and the dip before it. One bar a fiscal year (the Town's
        # label, the year the money can be spent); the state's proof where it reaches, the
        # Town's fact sheet for the years before it -- the two are equal where they overlap.
        chart=fc_chart,
        table=dict(caption='Certified free cash, two publishers', views=[
            dict(key='dls', label='The state’s proof', total_col=1, kinds=['ledger'] * 3,
                 columns=['Identified', 'Certified', 'Spent in'],
                 rows=dls_rows,
                 note='Division of Local Services free cash proof, labelled by the year of the '
                      '1 July balance it certifies. Spent in is the Town’s label for the same '
                      'money.'),
            dict(key='sheet', label='The Town’s fact sheet', total_col=0, kinds=['stated'] * 3,
                 columns=['Certified', 'Operating budget it divides by', 'Share'],
                 rows=sheet_rows,
                 note='The Free Cash Fact Sheet in the FY27 warrant packet, by the fiscal year '
                      'the money can be spent in. Its figures equal the state’s proof, one year '
                      'apart, wherever the two overlap.')]),
        said=[said_file('school-committee/2025-09-03-minutes-7385.txt',
                        'With respect to the unspent money, the money is not lost. The money is '
                        'still there, it is free cash and it is going to roll over. It is going '
                        'to be appropriated in one fashion or another.', 'School Committee')],
        sources=[src['dls'], src['sheet'], src['ar25'], src['d-proof'], src['d-sheet']],
        finding_figures={'a': U(c25)}, finding_allow=('1 July 2025',))

    # ------------------------------------------------ free cash: the guideline
    fs = sheet[2026]
    last10 = sorted(sheet)[-10:]
    if last10 != list(range(2017, 2027)):
        fail('the fact sheet’s last ten years are no longer FY2017-FY2026: %s' % last10)
    met = [fy for fy in last10 if sheet[fy]['pct'] >= 5.0]
    if met != [2022, 2023, 2026]:
        fail('the years at or above 5%% are no longer the three the Town names: %s' % met)
    base_orig, base_rev = M['budgetBase'], M['budgetRevised']
    sh_orig = round(100 * c25 / base_orig, 2)
    sh_rev = round(100 * c25 / base_rev, 2)
    if abs(sh_orig / 100 - M['currentShare']) > 0.0001:
        fail('model.freeCash.currentShare no longer matches certified / budgetBase')
    lo, hi = 100 * M['bandLow'], 100 * M['bandHigh']
    BAND = lambda: {'lo': P(lo, 0), 'hi': P(hi, 0)}
    out['free-cash-guideline'] = TP.page(
        'free-cash-guideline',
        'Free cash is %s of the budget, inside the %s to %s the Town cites; %s of the last %s '
        'years fell short.' % (C.pct(fs['pct'], 2), C.pct(lo, 0), C.pct(hi, 0),
                                         C.num(len(last10) - len(met)), C.num(len(last10))),
        [f('town-share', P(fs['pct'], 2), 'free cash as a share of budget, %s, Town’s figure'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('town-base', U(fs['base']), 'the prior-year budget the Town divides by',
           'published'),
         f('band', figure(lo, '%s to %s' % (C.pct(lo, 0), C.pct(hi, 0))),
           'the range the Town says the state recommends', 'published'),
         f('short', N(len(last10) - len(met), 'years'),
           'of the last %s below %s, on the Town’s figures' % (C.num(len(last10)), C.pct(lo, 0)),
           'published', {'n': N(len(last10)), 'lo': P(lo, 0)}),
         f('ours-orig', P(sh_orig, 2), 'the same, against the %s original budget (ours)'
           % C.fy(2026), 'estimate', {'y': F(2026)}),
         f('ours-rev', P(sh_rev, 2), 'against the revised budget at March 2026 (ours)',
           'estimate', allow=('March 2026',)),
         f('dls-text', None, 'the state’s own guidance on free cash levels', 'gap',
           closes='the Division of Local Services publication the 5-7% recommendation comes '
                  'from')],
        [con('On the Town’s figures, free cash reached %s in only %s of the last %s years.'
             % (C.pct(lo, 0), C.num(len(met)), C.num(len(last10))), ['short', 'town-share'],
             {'lo': P(lo, 0), 'n': N(len(met)), 'm': N(len(last10))}),
         con('Against three different budget figures, this year’s share is %s to %s: inside '
             'the range each time.' % (C.pct(sh_rev, 2), C.pct(fs['pct'], 2)),
             ['town-share', 'town-base', 'ours-orig', 'ours-rev'],
             {'a': P(sh_rev, 2), 'b': P(fs['pct'], 2)}),
         con('The %s range reaches this archive only as the Town quoting the state.'
             % ('%s to %s' % (C.pct(lo, 0), C.pct(hi, 0))), ['band', 'dls-text'], BAND(),
             notes=[step('Whether the town was short in most of the last ten years depends on '
                         'where that line sits, and the line rests on one paraphrase.', 'gap',
                         closes='the Division of Local Services’ own published guidance')])],
        # Drawn in dollars, not as the share: the bars are what was certified, the lines are
        # where the cited range sits against each year's budget. The lines are our arithmetic.
        chart=TP.series(
            'Free cash against the cited range', [C.fy(fy) for fy in last10],
            [TP.track('Certified, the Town’s fact sheet', [sheet[fy]['certified'] for fy in last10],
                      'stated', 'bar'),
             TP.track('Low end of the range (ours)', [lo / 100 * sheet[fy]['base'] for fy in last10],
                      'estimate', 'line'),
             TP.track('High end of the range (ours)', [hi / 100 * sheet[fy]['base']
                                                       for fy in last10], 'estimate', 'line')],
            '$', kind='bar',
            note='The range is the %s to %s the Town cites, times the prior-year budget its own '
                 'fact sheet divides by.' % (C.pct(lo, 0), C.pct(hi, 0)), note_figures=BAND()),
        table=dict(caption='Free cash against the budget, the Town’s figures', views=[dict(
            key='sheet', label='The Town’s fact sheet', total_col=2, kinds=['stated'] * 3,
            columns=['Certified', 'Operating budget', 'Share'], rows=sheet_rows,
            note='As printed in the Free Cash Fact Sheet. Each share recomputes from the two '
                 'figures beside it to the hundredth of a point.')]),
        said=[said_file('finance-committee/2026-05-28-minutes-7828.txt',
                        'Chris Menard suggests having an analyst review all of the town’s '
                        'policies on free cash and estimates.', 'Finance Committee')],
        sources=[src['sheet'], src['release'], src['dls'], src['d-sheet'], src['model']],
        finding_figures={'a': P(fs['pct'], 2), 'lo': P(lo, 0), 'hi': P(hi, 0),
                         'n': N(len(last10) - len(met)), 'm': N(len(last10))})

    # ------------------------------------------------ free cash: where it comes from
    c = comp[2025]
    under25, rec25 = c['underspend'], c['receipts']
    us25, us23 = 100 * c['shares']['underspend'], 100 * comp[2023]['shares']['underspend']
    if abs(under25 / c['identified'] - c['shares']['underspend']) > 0.0001:
        fail('the 2025 underspend share no longer recomputes')
    tot = FCJ['totals']
    line = next(b for b in tot['by_line'] if b['line'].startswith('Add Unencumbered'))
    us5 = 100 * line['amount'] / tot['identified']
    mult = {m['town']: m for m in FCJ['multiples']}
    lm = mult['Lunenburg']
    if max(FCJ['multiples'], key=lambda m: m['multiple'])['town'] != 'Lunenburg':
        fail('Lunenburg no longer has the highest underspend multiple of the nine towns')
    avg = sum(comp[y]['underspend'] for y in (2021, 2022, 2023, 2024)) / 4
    if abs(avg - lm['average']) > 0.5:
        fail('the multiple’s average is no longer 2021-2024')
    ux = next(p for p in M['peerComposition'] if p['town'] == 'Uxbridge')
    out['free-cash-sources'] = TP.page(
        'free-cash-sources',
        'Two thirds of the free cash identified in July %s, %s, was money appropriated and not '
        'spent.' % ('2025', C.usd(under25)),
        [f('under25', U(under25), 'appropriated and not spent, 2025', 'published',
           {'y': Y(2025)}),
         f('us25', P(us25), 'of identified free cash, 2025', 'published', {'y': Y(2025)}),
         f('rec25', U(rec25), 'local receipts above the estimate, 2025', 'published',
           {'y': Y(2025)}),
         f('us23', P(us23), 'unspent share in 2023', 'published', {'y': Y(2023)}),
         f('us5', P(us5), 'unspent share across all five years', 'published'),
         f('mult', figure(lm['multiple'], '%.2f times' % lm['multiple']),
           '2025’s unspent against the %s average' % '2021-2024', 'published',
           {'y': Y(2025)}, allow=('2021-2024',)),
         f('ux', P(100 * ux['unspentShare']), 'Uxbridge’s unspent share, 2025, the lowest',
           'published', {'y': Y(2025)}),
         f('dept-gap', None, 'which departments left the money unspent', 'gap',
           closes='the period 13 general ledger: budget, spent and turned back, by department'),
         f('school-gap', None, 'how much of it was the schools’', 'gap',
           closes='a departmental turnback schedule for the year-end close')],
        [con('Unspent appropriations rose from %s of free cash in %s to %s in %s.'
             % (C.pct(us23), '2023', C.pct(us25), '2025'), ['us23', 'us25', 'under25'],
             {'a': P(us23), 'y': Y(2023), 'b': P(us25), 'z': Y(2025)}),
         con('The %s unspent figure was %.2f times its %s average, the highest multiple of '
             '%s towns.' % ('2025', lm['multiple'], '2021-2024', 'nine'), ['mult', 'ux'],
             {'y': Y(2025), 'm': figure(lm['multiple'], '%.2f times' % lm['multiple'])},
             allow=('2021-2024',)),
         con('It is one town-wide figure; nothing published says which departments, or how '
             'much was the schools’.', ['dept-gap', 'school-gap', 'under25'],
             notes=[step('The Town’s FY27 budget release attributes the FY25 school surplus to '
                         'vacant posts and to salaries newly covered by grants. That is its '
                         'account; nothing here tests it.', 'hypothesis',
                         allow=('FY27', 'FY25'))])],
        chart=TP.series(
            'Unspent money inside free cash', [str(y) for y in sorted(comp)],
            [TP.track('Free cash identified', [comp[y]['identified'] for y in sorted(comp)],
                      'published', 'bar'),
             TP.track('Of it, appropriated and not spent', [comp[y]['underspend']
                                                            for y in sorted(comp)],
                      'published', 'bar')],
            '$', kind='bar',
            note='The state’s proof, by the year of the 1 July balance. The other parts net to '
                 'the rest, and in some years run below zero.', note_allow=('1 July',)),
        table=dict(caption='What Lunenburg’s free cash was made of', views=[dict(
            key='parts', label='The state’s proof', total_col=4, kinds=['ledger'] * 5,
            columns=['Not spent', 'Receipts above estimate', 'State aid against estimate',
                     'Everything else', 'Identified'],
            rows=[dict(label=str(y), cells=[C.usd(comp[y][k]) for k in
                                            ('underspend', 'receipts', 'aid', 'other',
                                             'identified')])
                  for y in sorted(comp, reverse=True)],
            note='Division of Local Services free cash proof, components grouped. Everything '
                 'else is prior free cash not appropriated and the smaller adjustments, net.')]),
        said=[said_file('finance-committee/2026-05-28-minutes-7828.txt',
                        'Ana Lockwood states for the last 10 years the town has not collected '
                        'less than 4 million dollars in local receipts. This year’s estimate is '
                        '3.535 million. Ana Lockwood suggests not being so conservative based on '
                        'the data.', 'Finance Committee')],
        sources=[src['dls'], src['release'], src['d-proof']],
        finding_figures={'a': U(under25), 'y': Y(2025)})

    # ------------------------------------------------ free cash and capital
    cap = {int(r['fy']): r for r in rows('capital-funding-history.csv')}
    CAP = M['capital']
    for fy, r in cap.items():
        parts = sum(float(r[k]) for k in ('free_cash', 'taxation',
                                          'unexpended_prior_year_capital', 'other'))
        if abs(parts - float(r['total'])) > 0.05:
            fail('FY%d capital funding does not foot: %.2f against %s' % (fy, parts, r['total']))
    largest = [fy for fy, r in cap.items()
               if float(r['free_cash']) >= max(float(r[k]) for k in
                                               ('taxation', 'unexpended_prior_year_capital',
                                                'other'))]
    fc26, t26 = float(cap[2026]['free_cash']), float(cap[2026]['total'])
    if round(fc26) != CAP['lastYear']['freeCash'] or round(t26) != CAP['lastYear']['total']:
        fail('model.freeCash.capital.lastYear no longer matches the funding table')
    p27, tot27 = CAP['plannedFromFreeCash'], CAP['programmeTotal']
    rst, conv = CAP['restrictedTotal'], CAP['convertibleTotal']
    if sum(i['cost'] for i in CAP['restrictedItems']) != rst or \
            p27 + CAP['plannedFromTaxation'] + rst != tot27:
        fail('the FY2027 capital programme no longer foots by source')
    queue = CAP['queueValue']
    out['free-cash-and-capital'] = TP.page(
        'free-cash-and-capital',
        'Free cash paid %s of the %s %s capital programme; %s plans %s of %s.'
        % (C.usd(fc26), C.usd(t26), C.fy(2026), C.fy(2027), C.usd(p27), C.usd(tot27)),
        [f('fc26', U(fc26), 'free cash into capital, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('t26', U(t26), 'the whole capital programme, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('fc25', U(float(cap[2025]['free_cash'])), 'free cash into capital, %s' % C.fy(2025),
           'published', {'y': F(2025)}),
         f('largest', N(len(largest), 'years'), 'of %s with free cash the largest source'
           % C.num(len(cap)), 'published', {'n': N(len(cap))}),
         f('p27', U(p27), 'free cash planned for %s' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('tot27', U(tot27), 'the whole %s programme' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('rst', U(rst), 'of it from the vehicle stabilization fund', 'published'),
         f('queue', U(queue), 'ranked, costed work below the %s line' % C.fy(2027),
           'published', {'y': F(2027)})],
        [con('Free cash was the capital plan’s largest source in %s of the %s years it '
             'publishes.' % (C.num(len(largest)), C.num(len(cap))), ['largest', 'fc26', 'fc25'],
             {'n': N(len(largest)), 'm': N(len(cap))}),
         con('%s of %s’s programme comes from a fund restricted to vehicles and equipment.'
             % (C.usd(rst), C.fy(2027)), ['rst', 'tot27'], {'a': U(rst), 'y': F(2027)},
             notes=[step('The plan footnotes two projects to that fund, and they sum to the '
                         'amount its funding page shows for it.', 'measured')]),
         con('Ranked projects worth %s already sit below the %s funding line.'
             % (C.usd(queue), C.fy(2027)), ['queue', 'p27'], {'a': U(queue), 'y': F(2027)})],
        chart=TP.series(
            'How capital was paid for', [C.fy(fy) for fy in sorted(cap)],
            [TP.track('Free cash', [float(cap[fy]['free_cash']) for fy in sorted(cap)],
                      'stated', 'bar'),
             TP.track('Taxation', [float(cap[fy]['taxation']) for fy in sorted(cap)],
                      'stated', 'bar'),
             TP.track('Other sources', [float(cap[fy]['unexpended_prior_year_capital'])
                                        + float(cap[fy]['other']) for fy in sorted(cap)],
                      'stated', 'bar')],
            '$', kind='bar', stacked=True,
            note='The capital plan’s own funding table. Other sources is unspent prior-year '
                 'capital and anything else it prints.'),
        table=dict(caption='How capital was paid for, by year', views=[dict(
            key='cap', label='The capital plan’s table', total_col=3, kinds=['stated'] * 4,
            columns=['Free cash', 'Taxation', 'Other sources', 'Total'],
            rows=[dict(label=C.fy(fy), cells=[
                C.usd(float(r['free_cash'])), C.usd(float(r['taxation'])),
                C.usd(float(r['unexpended_prior_year_capital']) + float(r['other'])),
                C.usd(float(r['total']))]) for fy, r in sorted(cap.items(), reverse=True)],
            note='The FY2027 capital plan’s own ten-year funding table. Other sources is unspent '
                 'prior-year capital and anything else the table prints.')]),
        sources=[src['capplan'], src['d-cap']],
        finding_figures={'a': U(fc26), 'b': U(t26), 'y': F(2026), 'z': F(2027), 'c': U(p27),
                         'd': U(tot27)})

    # ------------------------------------------------ free cash for schools (the lever)
    rung = next(l for l in M['ladder'] if abs(l['target'] - M['bandLow']) < 1e-9)
    redirect = rung['released']
    if abs(redirect - round(c25 - M['bandLow'] * base_orig)) > 1:
        fail('the 5% rung no longer equals certified less 5% of the budget')
    g28 = rung['covers'][0]
    if g28['fy'] != 28 or g28['covered']:
        fail('the 5% redirect now covers FY2028; this page says it does not')
    short28 = -g28['remaining']
    whole = M['ladder'][0]
    if whole['target'] != 0 or [x['covered'] for x in whole['covers'][:3]] != [True, True, False]:
        fail('the whole certification no longer covers exactly FY2028 and FY2029')
    gaps = {d['fy']: d['amount'] for d in M['deficits']}
    draw = next(d for d in CAP['atDraw'] if d['redirect'] == redirect)
    strict, reseq = draw['strictLost'], draw['resequencedLost']
    normal, nshare = M['normalCertified'], 100 * M['normalShare']
    mult26 = redirect / fc26
    out['free-cash-redirect'] = TP.page(
        'free-cash-redirect',
        'Kept above the %s floor, %s could be redirected, %s short of the %s gap (our '
        'arithmetic).' % (C.pct(lo, 0), C.usd(redirect), C.usd(short28), C.fy(2028)),
        [f('redirect', U(redirect), 'free cash above %s of the budget (ours)' % C.pct(lo, 0),
           'estimate', {'lo': P(lo, 0)}),
         f('gap28', U(gaps[28]), 'the projected school gap, %s (ours)' % C.fy(2028), 'estimate',
           {'y': F(2028)}),
         f('short28', U(short28), 'what the redirect leaves short that year (ours)', 'estimate'),
         f('gap30', U(gaps[30]), 'the projected gap, %s (ours)' % C.fy(2030), 'estimate',
           {'y': F(2030)}),
         f('strict', U(strict), 'capital work lost, plan’s ranking held (ours)', 'estimate'),
         f('reseq', U(reseq), 'capital work lost, queue re-ranked (ours)', 'estimate'),
         f('mult26', figure(mult26, '%.2f times' % mult26),
           'the redirect, against free cash into capital, %s' % C.fy(2026), 'estimate',
           {'y': F(2026)}),
         f('normal', U(normal), 'certified if unspent money were at its average (ours)', 'estimate'),
         f('nshare', P(nshare), 'of the budget, in that case (ours)', 'estimate')],
        [con('Kept to the %s floor, %s could be redirected; that is %s short of the %s gap.'
             % (C.pct(lo, 0), C.usd(redirect), C.usd(short28), C.fy(2028)),
             ['redirect', 'gap28', 'short28'],
             {'lo': P(lo, 0), 'a': U(redirect), 'b': U(short28), 'y': F(2028)}),
         con('All %s, guideline ignored, covers %s and %s; %s’s gap is %s.'
             % (C.usd(c25), C.fy(2028), C.fy(2029), C.fy(2030), C.usd(gaps[30])),
             ['gap28', 'gap30'],
             {'a': U(c25), 'y': F(2028), 'z': F(2029), 'w': F(2030), 'g': U(gaps[30])}),
         con('The redirect is %.2f times what free cash gave capital in %s; %s to %s of work '
             'stops.' % (mult26, C.fy(2026), C.usd(reseq), C.usd(strict)),
             ['mult26', 'strict', 'reseq'],
             {'m': figure(mult26, '%.2f times' % mult26), 'y': F(2026), 'a': U(reseq),
              'b': U(strict)},
             notes=[step('Which projects would stop depends on how the Capital Planning '
                         'Committee re-ranks a shorter list; nothing published says.', 'gap',
                         closes='any prior year’s recommended capital list beside its funded '
                                'list')]),
         con('Had unspent money sat at its %s average, free cash would be %s of the budget: '
             'under the floor.' % ('2021-2024', C.pct(nshare)), ['normal', 'nshare'],
             {'p': P(nshare)}, allow=('2021-2024',))],
        chart=TP.series(
            'The redirect against the gap',
            ['Certified, July 2025', 'Above the floor', 'Gap, %s' % C.fy(2028)],
            [TP.track('Certified by the state', [c25, None, None], 'published', 'bar'),
             TP.track('Our arithmetic', [None, redirect, gaps[28]], 'estimate', 'bar')],
            '$', kind='bar', stacked=True,
            note='Above the floor is what stays after keeping %s of the budget; the gap is the '
                 'model’s projection.' % C.pct(lo, 0), note_figures={'lo': P(lo, 0)}),
        said=[said_file('select-board/2025-03-11-minutes-7096.txt',
                        'The options discussed included a multi-year override or utilizing '
                        'one-time funds specifically free cash as a stopgap, however these funds '
                        'should not be used in an operating budget, but as a one-time '
                        'appropriation.', 'Select Board')],
        sources=[src['dls'], src['release'], src['capplan'], src['model']],
        finding_figures={'lo': P(lo, 0), 'a': U(redirect), 'b': U(short28), 'y': F(2028)})

    # ------------------------------------------------ stabilization: the accounts
    trust = [r for r in rows('trust-agency-balances.csv') if r['group'] == 'STABILIZATION FUNDS']
    held = sum(float(r['held']) for r in trust)
    if abs(held - SF['totals']['held']) > 0.01 or len(trust) != SF['totals']['funds']:
        fail('the ledger’s stabilization accounts no longer match stabilization-funds.json')
    for r in trust:
        if abs(float(r['held']) + float(r['beginning'])) > 0.005:
            fail('%s: `held` is no longer the opening balance' % r['account'])
        rem = -float(r['remaining'])
        if abs(float(r['held']) - float(r['revenue']) - float(r['expenditure'] or 0) - rem) > 0.01:
            fail('%s does not foot: opening + in - out != remaining' % r['account'])
    acct = {r['account']: r for r in trust}
    rem_tot = sum(-float(r['remaining']) for r in trust)
    in_tot = sum(-float(r['revenue']) for r in trust)
    out_tot = sum(float(r['expenditure'] or 0) for r in trust)
    gen = float(acct['8124']['held'])
    gen_rem = -float(acct['8124']['remaining'])
    gen_in = -float(acct['8124']['revenue'])
    other2 = float(acct['8137']['held']) + float(acct['8125']['held'])
    restricted = held - gen
    if abs(gen - SF['totals']['general']) > 0.01:
        fail('the general fund’s balance no longer matches the payload')
    out['stabilization-balances'] = TP.page(
        'stabilization-balances',
        'The town’s ledger files %s under its %s stabilization accounts, at the start of %s.'
        % (C.usd(held), 'nine', C.fy(2026)),
        [f('held', U(held), 'in the %s accounts, 1 July 2025 (ledger)' % 'nine', 'published',
           allow=('1 July 2025',)),
         f('gen', U(gen), 'the general Stabilization Fund, account 8124', 'published',
           allow=('8124',)),
         f('veh', U(float(acct['8136']['held'])), 'vehicle and equipment, account 8136',
           'published', allow=('8136',)),
         f('other2', U(other2), 'an OPEB trust and a conservation fund', 'published'),
         f('in', U(in_tot), 'come in, July 2025 to March 2026', 'published',
           allow=('July 2025', 'March 2026')),
         f('out', U(out_tot), 'paid out in the same months', 'published'),
         f('rem', U(rem_tot), 'held at 31 March 2026', 'published', allow=('31 March 2026',)),
         f('in-gap', None, 'how much of what came in is interest', 'gap',
           closes='the MUNIS revenue detail for each trust account')],
        [con('%s of it is an OPEB trust and a conservation fund, which the ledger files with '
             'the others.' % C.usd(other2), ['other2', 'held'], {'a': U(other2)}),
         con('Nothing was paid out of any account by 31 March 2026, and %s came in.'
             % C.usd(in_tot), ['in', 'out', 'rem', 'in-gap'], {'a': U(in_tot)},
             allow=('31 March 2026',),
             notes=[step('Nine months are not a year, and they say nothing about whether these '
                         'funds get spent.', 'gap',
                         closes='the period 13 trust and agency report for the year',
                         allow=('period 13',))])],
        chart=dict(id='stabilization-holdings', source='/data/stabilization-funds.json'),
        table=dict(caption='The nine accounts, as the ledger prints them', views=[dict(
            key='ledger', label='MUNIS trust and agency report', total_col=3,
            kinds=['ledger'] * 4,
            columns=['Held, 1 July 2025', 'In since', 'Out since', 'Held, 31 March 2026'],
            rows=[dict(label='%s %s' % (r['account'], r['name']), cells=[
                usd2(r['held']), usd2(-float(r['revenue'])), usd2(float(r['expenditure'] or 0)),
                usd2(-float(r['remaining']))])
                for r in sorted(trust, key=lambda r: -float(r['held']))] + [dict(
                    label='All nine', cells=[usd2(held), usd2(in_tot), usd2(out_tot),
                                             usd2(rem_tot)])],
            note='The account numbers and names are the ledger’s own. The report foots to the '
                 'system’s subtotals; obtained by a public records request.')]),
        sources=[src['trust'], src['d-trust']],
        finding_figures={'a': U(held), 'y': F(2026)})

    # ------------------------------------------------ the general fund, year by year
    ser = next(s for s in SF['series'] if s['fund'] == 'Stabilization')
    pts = {p['fy']: p for p in ser['points']}
    if sorted(pts) != list(range(2011, 2026)):
        fail('the general fund series no longer runs FY2011-FY2025 without a gap')
    if abs(pts[2025]['ending_cash'] - gen) > 0.01:
        fail('the series’ FY2025 close no longer equals the ledger’s opening balance')
    cash = {fy: p['ending_cash'] for fy, p in pts.items()}
    if not all(cash[y] > cash[y - 1] for y in range(2013, 2026)) or not cash[2012] < cash[2011]:
        fail('the general fund no longer fell in FY2012 and rose every year after')
    rate = ((cash[2025] / cash[2011]) ** (1 / 14) - 1) * 100
    if abs(rate - ser['rate']) > 0.01:
        fail('the series rate no longer recomputes: %.3f against %.3f' % (rate, ser['rate']))
    gshare = 100 * gen / base_orig
    out['general-stabilization-fund'] = TP.page(
        'general-stabilization-fund',
        'The general fund’s cash rose every year from %s to %s, to %s.'
        % (C.fy(2012), C.fy(2025), C.usd(cash[2025])),
        [f('fy11', U(cash[2011]), 'cash at the %s close' % C.fy(2011), 'published',
           {'y': F(2011)}),
         f('fy12', U(cash[2012]), 'at the %s close, the low' % C.fy(2012), 'published',
           {'y': F(2012)}),
         f('fy23', U(cash[2023]), 'at the %s close' % C.fy(2023), 'published', {'y': F(2023)}),
         f('fy25', U(cash[2025]), 'at the %s close' % C.fy(2025), 'published', {'y': F(2025)}),
         f('rate', P(rate), 'a year, %s to %s, compounded' % (C.fy(2011), C.fy(2025)),
           'published', {'a': F(2011), 'b': F(2025)}),
         f('mar26', U(gen_rem), 'held at 31 March 2026 (ledger)', 'published',
           allow=('31 March 2026',)),
         f('gin', U(gen_in), 'come in since 1 July 2025', 'published', allow=('1 July 2025',)),
         f('policy', P(lo, 0), 'of the budget: the level the Town’s policy names first',
           'published'),
         f('gshare', P(gshare), 'what it holds, against the %s budget (ours)' % C.fy(2026),
           'estimate', {'y': F(2026)}),
         f('mix-gap', None, 'how much of the rise is deposits and how much interest', 'gap',
           closes='the MUNIS trust fund report for each year, with revenue split by source')],
        [con('The fund grew %s a year from %s to %s, and rose in every year after %s.'
             % (C.pct(rate), C.fy(2011), C.fy(2025), C.fy(2012)),
             ['fy11', 'fy12', 'fy25', 'rate', 'mix-gap'],
             {'r': P(rate), 'a': F(2011), 'b': F(2025), 'c': F(2012)}),
         con('At %s of the %s budget, by our arithmetic, it sits above the %s the Town’s '
             'policy names.' % (C.pct(gshare), C.fy(2026), C.pct(lo, 0)),
             ['gshare', 'policy', 'fy25'], {'p': P(gshare), 'y': F(2026), 'lo': P(lo, 0)},
             notes=[step('The policy says the omnibus budget; we divide by the original '
                         'appropriation, and the two may differ.', 'gap',
                         closes='the Town’s adopted financial policies, which the fact sheet '
                                'quotes')]),
         con('No withdrawal from the general fund appears in any vote this archive has read.',
             ['fy23', 'fy25'],
             notes=[step('That is a floor: money also leaves inside articles about something '
                         'else, and the record here starts in %s.' % C.fy(2011), 'gap',
                         {'y': F(2011)},
                         closes='the MUNIS trust fund report of expenditures by year')])],
        chart=TP.series(
            'The general Stabilization Fund', [C.fy(fy) for fy in sorted(cash)],
            [TP.track('Cash at the year’s close', [cash[fy] for fy in sorted(cash)],
                      'published', 'bar')],
            '$', kind='bar',
            note='Each year off the annual report’s trust table, published only where its own '
                 'arithmetic closes; the last is the ledger’s opening balance.'),
        table=dict(caption='The general Stabilization Fund at each year’s close', views=[dict(
            key='series', label='Trust tables and the ledger', total_col=0,
            kinds=['ledger'] * 2, columns=['Ending cash', 'Ending market value'],
            rows=[dict(label=C.fy(fy), cells=[usd2(p['ending_cash']),
                                              usd2(p['ending_market'])
                                              if p.get('ending_market') else None])
                  for fy, p in sorted(pts.items(), reverse=True)],
            note='Each year read off the annual report’s trust table and published only where '
                 'the table’s own arithmetic closes; the latest year is the ledger’s opening '
                 'balance. A dash is a market value the year does not print.')]),
        said=[said_file('select-board/2025-01-14-minutes-6957.txt',
                        'She added that Lunenburg’s stabilization funds are looking good and '
                        'that there is a strong commitment from the community to put away money '
                        'into stabilization funds of various types and that should continue.',
                        'Select Board')],
        sources=[src['ar25'], src['ar24'], src['ar23'], src['trust'], src['sheet'],
                 src['d-stab'], src['d-trust']],
        finding_figures={'a': F(2012), 'b': F(2025), 'c': U(cash[2025])})

    # ------------------------------------------------ who may spend it
    created = {c_['fund'] for c_ in SF['creations']}
    missing = SF['missing_creations']
    named = len(created) + len(missing)
    sheet_text = norm(open(os.path.join(ROOT, 'sources', 'budget-workbooks', 'finance-committee',
                                        'fy27-budget', 'tm-warrant', 'text',
                                        'free-cash-fact-sheet.docx.txt'),
                           encoding='utf-8').read())
    for words in ('increase the balance of the Stabilization Account if necessary to a level of '
                  'at least five percent of the current fiscal year omnibus budget',
                  'at last 10% of the previous fiscal year’s certified General Fund Free Cash '
                  'for deposit into the OPEB Trust Fund'):
        if words not in sheet_text:
            fail('the fact sheet no longer quotes the policy as %r' % words)
    out['who-may-spend-it'] = TP.page(
        'who-may-spend-it',
        'Only the general fund, %s of %s, may go to any lawful use, by a two-thirds vote.' % (C.usd(gen), C.usd(held)),
        [f('gen', U(gen), 'may be spent on any lawful purpose', 'published'),
         f('restricted', U(restricted), 'held for a stated purpose (our split)', 'estimate'),
         f('vote', figure(2 / 3, 'two-thirds'), 'of Town Meeting to spend from one, c.40 §5B',
           'statute', allow=('c.40 §5B',)),
         f('created', N(len(created), 'funds'), 'of %s in the votes with a creating article '
           'here' % C.num(named), 'published', {'n': N(named)}),
         f('policy1', P(lo, 0), 'of the budget: free cash goes here first, by policy',
           'published'),
         f('policy2', P(10, 0), 'of last year’s free cash to the OPEB trust, second',
           'published'),
         f('purpose-gap', None, 'what the funds created before %s may be spent on'
           % C.fy(2011), 'gap', {'y': F(2011)},
           closes='the Town Meeting articles that created them, in warrants before FY2011')],
        [con('The other %s is held for stated purposes; that split is ours, read off each '
             'fund’s name.' % C.usd(restricted), ['restricted', 'gen'], {'a': U(restricted)}),
         con('For %s funds, the general one among them, no creating article is in this archive.'
             % C.num(len(missing)), ['created', 'purpose-gap'], {'n': N(len(missing))},
             notes=[step('Where the article is missing, a fund’s purpose rests on its name, '
                         'which is a reading and not a rule.', 'gap',
                         closes='the creating Town Meeting articles')]),
         con('The Town’s free cash policy puts topping the general fund up to %s of the budget '
             'first.' % C.pct(lo, 0), ['policy1', 'policy2', 'gen'], {'lo': P(lo, 0)},
             notes=[step('This archive holds the policy as the fact sheet quotes it, not the '
                         'adopted document.', 'gap',
                         closes='the Town’s adopted financial policies, Section 3.03',
                         allow=('3.03',))])],
        chart=TP.parts(
            'Who may spend the stabilization money',
            [('General fund, any lawful use', gen),
             ('Vehicle and equipment', float(acct['8136']['held'])),
             ('OPEB trust', float(acct['8137']['held'])),
             ('Conservation trust', float(acct['8125']['held'])),
             ('The other funds, each for a purpose',
              held - gen - float(acct['8136']['held']) - float(acct['8137']['held'])
              - float(acct['8125']['held']))],
            '$',
            note='Opening balances, 1 July 2025, as the ledger prints them. Which purpose each '
                 'fund serves is read from its name; that reading is ours.',
            note_allow=('1 July 2025',)),
        sources=[src['trust'], src['sheet'], src['d-votes'], src['d-trust']],
        finding_figures={'a': U(gen), 'b': U(held)})

    # ------------------------------------------------ deposits
    dep, garbled, fl = deposits()
    n_fc = sum(1 for d in dep if d['free_cash'])
    dep_tot = sum(d['amount'] for d in dep)
    first = min(d['fy'] for d in dep)
    by = {}
    for d in dep:
        by.setdefault(d['fy'], {'general': 0.0, 'special': 0.0, 'fc': 0, 'n': 0})
        by[d['fy']][d['fund']] += d['amount']
        by[d['fy']]['n'] += 1
        by[d['fy']]['fc'] += d['free_cash']
    g24 = sum(d['amount'] for d in dep if d['fy'] == 2024 and d['fund'] == 'general')
    s24 = sum(d['amount'] for d in dep if d['fy'] == 2024 and d['fund'] == 'special')
    plan = {r['item']: float(r['value']) for r in rows('free-cash-fy26.csv')
            if r['version'] == '2.27.25'}
    planned = plan['General Purpose Stabiliztion Fund'] + plan['Special Purpose Stabilization Fund(s)']
    if planned != g24 + s24:
        fail('the May 2025 plan no longer matches the May 2024 deposits; reword the page')
    payload_dep = SF['flows']['deposits_total']
    raw = sum(d['amount'] for d in fl['deposits'])
    if abs(payload_dep - raw) > 0.01:
        fail('stabilization-funds.json deposits no longer equal flows(); re-read both')
    out['stabilization-deposits'] = TP.page(
        'stabilization-deposits',
        'Town Meeting put %s into the two town funds in May 2024, and passed over both '
        'articles in May 2025.' % C.usd(g24 + s24),
        [f('g24', U(g24), 'into the general fund, May 2024', 'published', allow=('May 2024',)),
         f('s24', U(s24), 'into the special purpose fund, May 2024', 'published',
           allow=('May 2024',)),
         f('passed-over', N(2, 'articles'), 'for the same two funds, passed over, May 2025',
           'published', allow=('May 2025',)),
         f('planned', U(planned), 'planned for them in February 2025, from free cash',
           'published', allow=('February 2025',)),
         f('total', U(dep_tot), 'voted into the two funds, %s to %s, at least'
           % (C.fy(first), C.fy(2024)), 'published', {'a': F(first), 'b': F(2024)}),
         f('n-fc', N(n_fc, 'articles'), 'of %s that name free cash as a source'
           % C.num(len(dep)), 'published', {'n': N(len(dep))}),
         f('why-gap', None, 'why the May 2025 articles were passed over', 'gap',
           allow=('May 2025',),
           closes='the 2025 Annual Town Meeting minutes or the motion made on articles 16 '
                  'and 17')],
        [con('%s of %s deposits into the two funds name free cash as their source.'
             % (C.num(n_fc), C.num(len(dep))), ['n-fc', 'total'],
             {'a': N(n_fc), 'b': N(len(dep))},
             notes=[step('A deposit that would have come from free cash, if not made, leaves '
                         'the money in free cash: it is not a second pot.', 'measured')]),
         con('In February 2025, %s was planned for the two funds; in May both articles were '
             'passed over.' % C.usd(planned), ['planned', 'passed-over', 'why-gap'],
             {'a': U(planned)}, allow=('February 2025',)),
         con('The same %s had gone in the May before: %s to the general fund, %s to special '
             'purpose.' % (C.usd(g24 + s24), C.usd(g24), C.usd(s24)),
             ['g24', 's24'], {'a': U(g24 + s24), 'b': U(g24), 'c': U(s24)})],
        # Every fiscal year from the first deposit to the passed-over May 2025 articles. A
        # year with no passed deposit in the votes read is a GAP, not a zero -- the record is
        # a floor. FY2025 is a real zero: both articles were moved and passed over.
        chart=TP.series(
            'Deposits into the two town funds', [C.fy(y) for y in range(first, 2026)],
            [TP.track('General Stabilization Fund',
                      [0 if y == 2025 else (by[y]['general'] or None) if y in by else None
                       for y in range(first, 2026)], 'published', 'bar'),
             TP.track('Special purpose fund',
                      [0 if y == 2025 else (by[y]['special'] or None) if y in by else None
                       for y in range(first, 2026)], 'published', 'bar')],
            '$', kind='bar', stacked=True,
            note='Passed votes only. %s is a true zero: both articles were passed over. A '
                 'missing bar is a year with no passed deposit in the votes read.' % C.fy(2025),
            note_figures={'y': F(2025)}),
        table=dict(caption='Deposits into the two town funds, as Town Meeting voted them',
                   views=[dict(
            key='votes', label='Town Meeting votes', total_col=2, kinds=['ledger'] * 4,
            columns=['General fund', 'Special purpose fund', 'Both', 'Articles naming free cash'],
            rows=[dict(label=C.fy(fy), cells=[C.usd(v['general']) if v['general'] else None,
                                              C.usd(v['special']) if v['special'] else None,
                                              C.usd(v['general'] + v['special']),
                                              '%d of %d' % (v['fc'], v['n'])])
                  for fy, v in sorted(by.items(), reverse=True)],
            note='Passed votes only. The %s special purpose article prints its amount as '
                 '“$08,222.”, with a digit missing, and is left out. The special purpose fund '
                 'is the one the ledger calls vehicle equipment.' % C.fy(garbled['fy']))]),
        sources=[src['ar24'], src['ar25'], src['fcplan'], src['d-votes'], src['d-fcplan']],
        finding_figures={'a': U(g24 + s24)}, finding_allow=('May 2024', 'May 2025'))

    # ------------------------------------------------ withdrawals
    wd, failed = withdrawals(fl)
    if any(w['fund'].startswith('Stabilization Fund (general)') or w['fund'] == 'Stabilization'
           for w in wd):
        fail('a withdrawal from the general fund now appears; the pages say none does')
    wd_tot = sum(w['amount'] for w in wd)
    sewer = sum(1 for w in wd if 'Sewer' in w['fund'] or 'Inflow' in w['fund'])
    if len(failed) != 1 or failed[0]['amount'] != 986000.0:
        fail('the defeated withdrawal is no longer the one this page names')
    stab = rows('stabilization-balances.csv')
    h23 = next(float(r['ending_cash']) for r in stab
               if r['fy'] == '2023' and r['name'] == 'HEALTH INSURANCE STABILIZATION')
    h25 = float(acct['8140']['held'])
    hout = sum(w['amount'] for w in wd if w['fund'].startswith('Health'))
    out['stabilization-withdrawals'] = TP.page(
        'stabilization-withdrawals',
        'The record shows %s taken from stabilization funds in %s votes, none from the general '
        'fund.' % (C.usd(wd_tot), C.num(len(wd))),
        [f('wd', U(wd_tot), 'withdrawn, in the votes this archive can read', 'published'),
         f('n', N(len(wd), 'votes'), 'that took money out', 'published'),
         f('sewer', N(sewer, 'votes'), 'of them paying for the sewer system', 'published'),
         f('h23', U(h23), 'Health Insurance fund, %s close' % C.fy(2023), 'published',
           {'y': F(2023)}),
         f('h25', U(h25), 'the same fund, %s close' % C.fy(2025), 'published', {'y': F(2025)}),
         f('hout', U(hout), 'of that fall the record prints', 'published'),
         f('defeated', U(failed[0]['amount']), 'draw for an ambulance and trucks, defeated',
           'published'),
         f('wd-gap', None, 'everything that left these funds, year by year', 'gap',
           closes='the MUNIS trust fund reports of expenditure, by account and year')],
        [con('The Health Insurance fund fell from %s to %s in two years; the record prints %s '
             'of that.' % (C.usd(h23), C.usd(h25), C.usd(hout)), ['h23', 'h25', 'hout', 'wd-gap'],
             {'a': U(h23), 'b': U(h25), 'c': U(hout)}),
         con('%s of the %s withdrawals paid for the sewer system, from sewer funds.'
             % (C.num(sewer), C.num(len(wd))), ['sewer', 'n', 'wd'],
             {'a': N(sewer), 'b': N(len(wd))}),
         con('In November 2023 Town Meeting defeated a %s draw on the special purpose fund, '
             '%s to %s.' % (C.usd(failed[0]['amount']), '29', '92'), ['defeated'],
             {'a': U(failed[0]['amount'])}, allow=('November 2023', '29', '92'))],
        chart=TP.ranking(
            'Money withdrawn, by fund',
            sorted({w['fund']: sum(x['amount'] for x in wd if x['fund'] == w['fund'])
                    for w in wd}.items()), '$',
            note='Passed votes this archive can read, summed by fund. None draws on the general '
                 'Stabilization Fund.'),
        table=dict(caption='Money out of the stabilization funds, as printed', views=[dict(
            key='out', label='Votes that took money out', total_col=0, kinds=['ledger'],
            columns=['Amount'],
            rows=[dict(label='%s, %s' % (C.fy(w['fy']), w['fund']), cells=[usd2(w['amount'])])
                  for w in wd],
            note='Clauses inside other Town Meeting articles, read from the annual reports, and '
                 'one article that was itself a withdrawal. Passed votes only.')]),
        sources=[src['ar23'], src['ar24'], src['trust'], src['d-flows'], src['d-votes'],
                 src['d-stab']],
        finding_figures={'a': U(wd_tot), 'n': N(len(wd))})

    # ------------------------------------------------ reserves against the gap
    og = {g[0]: g[1] for g in SO['gaps']}
    for fy, amt in gaps.items():
        if og.get(fy) != amt:
            fail('FY20%d: the option page’s gap and the model’s differ' % fy)
    left, burn = gen, []
    for fy in sorted(og):
        cov = min(left, og[fy])
        left -= cov
        burn.append(dict(fy=fy, gap=og[fy], covered=cov, left=left, shortfall=og[fy] - cov))
        if left <= 0:
            break
    for a, b in zip(burn, SO['burndown']):
        if any(abs(a[k] - b[k]) > 0.01 for k in ('gap', 'covered', 'left', 'shortfall')):
            fail('the burndown no longer recomputes for FY20%d' % a['fy'])
    enter30 = burn[1]['left']
    short30 = burn[2]['shortfall']
    ct = SO['contingency']
    out['reserves-and-the-gap'] = TP.page(
        'reserves-and-the-gap',
        'Spent on the school gap, the general fund covers %s and %s and runs out in %s, by '
        'our arithmetic.' % (C.fy(2028), C.fy(2029), C.fy(2030)),
        [f('gen', U(gen), 'general fund at 1 July 2025, where the arithmetic starts', 'published',
           allow=('1 July 2025',)),
         f('g28', U(og[28]), 'projected gap, %s (ours)' % C.fy(2028), 'estimate',
           {'y': F(2028)}),
         f('g29', U(og[29]), 'projected gap, %s (ours)' % C.fy(2029), 'estimate',
           {'y': F(2029)}),
         f('g30', U(og[30]), 'projected gap, %s (ours)' % C.fy(2030), 'estimate',
           {'y': F(2030)}),
         f('enter30', U(enter30), 'left in the fund entering %s (ours)' % C.fy(2030),
           'estimate', {'y': F(2030)}),
         f('short30', U(short30), 'still short in %s (ours)' % C.fy(2030), 'estimate',
           {'y': F(2030)}),
         f('snow', U(ct['snow_over']), 'snow spending over budget, %s, at June' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('rf', U(ct['reserve']), 'the Reserve Fund, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('rating-gap', None, 'what a rating agency would make of spending it', 'gap',
           closes='the town’s bond rating report and most recent official statement')],
        [con('The fund enters %s with %s against a %s gap, and is empty that year.'
             % (C.fy(2030), C.usd(enter30), C.usd(og[30])), ['enter30', 'g30', 'short30'],
             {'y': F(2030), 'a': U(enter30), 'b': U(og[30])},
             notes=[step('The arithmetic models no interest and assumes the whole balance is '
                         'voted to the schools at once, keeping nothing back.', 'gap',
                         closes='a Town Meeting vote; no document can settle it')]),
         con('One snow year, %s, ran %s over budget; the Reserve Fund behind it held %s.'
             % (C.fy(2026), C.usd(ct['snow_over']), C.usd(ct['reserve'])), ['snow', 'rf', 'gen'],
             {'y': F(2026), 'a': U(ct['snow_over']), 'b': U(ct['reserve'])}),
         con('Nothing in this archive says what spending the fund would do to the town’s '
             'borrowing.', ['rating-gap'])],
        # Each year's projected gap, split into what the fund covers and what is still short.
        # The registry burndown drew only the covered years, unlabelled as ours.
        chart=TP.series(
            'The school gap and the general fund', ['FY20%d' % b['fy'] for b in burn],
            [TP.track('Covered by the general fund (ours)', [b['covered'] for b in burn],
                      'estimate', 'bar'),
             TP.track('Still short (ours)', [b['shortfall'] for b in burn], 'estimate', 'bar')],
            '$', kind='bar', stacked=True,
            note='Each bar is the model’s projected gap. The fund starts at its 1 July 2025 '
                 'balance, earns nothing, and is spent whole on the schools.',
            note_allow=('1 July 2025',)),
        said=[said_file('finance-committee/2025-03-13-minutes-7009.txt',
                        'if there is a direct impact on the town’s bond rating if the town does '
                        'not contribute to OPEB', 'Finance Committee')],
        sources=[src['trust'], src['d-trust'], src['model']],
        finding_figures={'a': F(2028), 'b': F(2029), 'c': F(2030)})

    # ------------------------------------------------ the two hubs
    # Split 14 October 2026 (TJ: "Yes, split free cash and stabilization funds"): free cash is
    # a subject a reader searches for by name, so it has its own shelf and hub at /free-cash.
    # The stabilization funds keep /town-reserves. Every fact and conclusion below was on the
    # single combined hub, or is a figure the topic pages under each hub already state.
    if len(trust) != 9:
        fail('the ledger no longer holds nine stabilization accounts; the hub answer says nine')
    h = {}
    h['h-cert'] = f('h-cert', U(c25), 'free cash certified as of 1 July 2025', 'published',
                    allow=('1 July 2025',))
    h['h-under'] = f('h-under', P(us25), 'of it appropriated and not spent', 'published')
    h['h-share'] = f('h-share', P(fs['pct'], 2), 'free cash as a share of budget, %s, Town’s '
                     'figure' % C.fy(2026), 'published', {'y': F(2026)})
    h['h-short'] = f('h-short', N(len(last10) - len(met), 'years'),
                     'of the last %s below %s, on the Town’s figures'
                     % (C.num(len(last10)), C.pct(lo, 0)), 'published',
                     {'n': N(len(last10)), 'lo': P(lo, 0)})
    h['h-capital'] = f('h-capital', U(fc26), 'free cash into capital, %s' % C.fy(2026),
                       'published', {'y': F(2026)})
    h['h-redirect'] = f('h-redirect', U(redirect), 'free cash above %s of the budget (ours)'
                        % C.pct(lo, 0), 'estimate', {'lo': P(lo, 0)})
    h['h-band-gap'] = f('h-band-gap', None, 'the state’s own free cash guideline', 'gap',
                        closes='the Division of Local Services publication the Town paraphrases')
    h['h-dept-gap'] = f('h-dept-gap', None, 'which departments left free cash unspent', 'gap',
                        closes='the period 13 general ledger, turnback by department')
    s_ = {}
    s_['h-held'] = f('h-held', U(held), 'in %s stabilization accounts, 1 July 2025' % 'nine',
                     'published', allow=('1 July 2025',))
    s_['h-gen'] = f('h-gen', U(gen), 'of it in the general fund, any lawful use', 'published')
    s_['h-restricted'] = f('h-restricted', U(restricted), 'held for stated purposes (our split)',
                           'estimate')
    s_['h-fromfc'] = f('h-fromfc', N(n_fc, 'articles'), 'of %s deposits naming free cash'
                       % C.num(len(dep)), 'published', {'n': N(len(dep))})
    s_['h-years'] = f('h-years', N(2, 'years'), 'of the school gap the general fund covers (ours)',
                      'estimate')
    s_['h-out-gap'] = f('h-out-gap', None, 'every withdrawal from the funds, by year', 'gap',
                        closes='the MUNIS trust fund reports of expenditure')
    if len([b for b in burn if b['shortfall'] == 0]) != 2:
        fail('the general fund no longer covers exactly two years of the gap')

    fc_ladder = LD.ladder([
        LD.tier('What is held', [h['h-cert'], h['h-under'], h['h-share'], h['h-short']]),
        LD.tier('Where it goes', [h['h-capital'], h['h-redirect']]),
        LD.tier('What is not settled', [h['h-band-gap'], h['h-dept-gap']]),
    ], [
        LD.conclusion('Free cash reached a record %s in July %s; %s of it was money '
                      'appropriated and not spent.' % (C.usd(c25), '2025', C.pct(us25)),
                      ['h-cert', 'h-under'], {'a': U(c25), 'y': Y(2025), 'p': P(us25)}),
        LD.conclusion('On the Town’s figures, free cash reached %s in only %s of the last %s '
                      'years.' % (C.pct(lo, 0), C.num(len(met)), C.num(len(last10))),
                      ['h-short', 'h-share'],
                      {'lo': P(lo, 0), 'n': N(len(met)), 'm': N(len(last10))}),
        LD.conclusion('Free cash is also the capital plan’s money: %s of the %s programme.'
                      % (C.usd(fc26), C.fy(2026)), ['h-capital'], {'a': U(fc26), 'y': F(2026)}),
        LD.conclusion('Kept to the %s floor, %s could be redirected to the school gap (our arithmetic).'
                      % (C.pct(lo, 0), C.usd(redirect)), ['h-redirect', 'h-share'],
                      {'lo': P(lo, 0), 'a': U(redirect)}),
        LD.conclusion('The state’s guideline itself, and which departments left money unspent, '
                      'are not published here.', ['h-band-gap', 'h-dept-gap']),
    ])
    out['free-cash'] = TP.hub(
        'free-cash',
        'The state certified %s of free cash as of 1 July %s, the most the Town’s records list; '
        '%s of it was money appropriated and not spent.' % (C.usd(c25), '2025', C.pct(us25)),
        fc_ladder, chart=fc_chart,
        answer_figures={'a': U(c25), 'y': Y(2025), 'p': P(us25)}, answer_allow=('1 July',))

    st_ladder = LD.ladder([
        LD.tier('What is held', [s_['h-held'], s_['h-gen'], s_['h-restricted']]),
        LD.tier('Money in and out', [s_['h-fromfc'], s_['h-years'], s_['h-out-gap']]),
    ], [
        LD.conclusion('Of %s in stabilization accounts, only the general fund’s %s may go to any '
                      'lawful use.' % (C.usd(held), C.usd(gen)),
                      ['h-held', 'h-gen', 'h-restricted'], {'a': U(held), 'b': U(gen)}),
        LD.conclusion('%s of %s deposits into the two town stabilization funds name free cash '
                      'as their source.' % (C.num(n_fc), C.num(len(dep))), ['h-fromfc'],
                      {'a': N(n_fc), 'b': N(len(dep))}),
        LD.conclusion('Spent on the school gap, the general fund covers %s and %s, by our '
                      'arithmetic.' % (C.fy(2028), C.fy(2029)), ['h-years', 'h-gen'],
                      {'a': F(2028), 'b': F(2029)}),
        LD.conclusion('Every withdrawal from the funds, year by year, is not published here.',
                      ['h-out-gap']),
    ])
    out['town-reserves'] = TP.hub(
        'town-reserves',
        'The town holds %s in %s stabilization accounts as of 1 July %s. Only the general '
        'fund’s %s may be spent on anything lawful.' % (C.usd(held), 'nine', '2025', C.usd(gen)),
        st_ladder,
        chart=dict(id='stabilization-holdings', source='/data/stabilization-funds.json'),
        answer_figures={'b': U(held), 'y': Y(2025), 'c': U(gen)},
        answer_allow=('1 July',))

    HUBS = ('free-cash', 'town-reserves')
    if sorted(k for k in out if k not in HUBS) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ (set(out) - set(HUBS))))
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = []
        for p, text in outs.items():
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                stale.append(os.path.relpath(p, ROOT))
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('town reserves topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
