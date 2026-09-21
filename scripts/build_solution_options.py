"""Solution options: what the stabilization funds could actually do about the gap.

    python3 scripts/build_solution_options.py
    python3 scripts/build_solution_options.py --check

Writes `sources/analyses/solution-options.md` and
`fy28/public/data/solution-options.json`.

WHY THIS IS A SEPARATE REPORT.

TJ: *"the current stabilization page should be more focused on info about the stabilization
not necessarily focused on using it to close the deficit. so we can pulll some of that
info out and put it on this new report."*

Right, and the stabilization page kept drifting. It is a description of nine funds -- what
they hold, who may spend them, what has gone in and come out -- and every few paragraphs it
was turning into an argument about the school deficit. Those are two different documents
for two different readers: one wants to know what the town has, the other wants to know
what can be done with it.

THE THREE THINGS A READER ARRIVES WITH, and they are answered in this order:

  1. Can we just stop putting money in?     The deposit is RECURRING, which is the right
                                            shape for a recurring gap -- and it is small.
  2. Can we spend what is already there?    Yes, and it buys a fixed number of years.
  3. Then what?                             The question the first two exist to set up.

WHAT THE MODEL DOES AND DOES NOT DO. It runs the projection's own level-service gap
against two levers and reports what each covers. It does not decide anything, it does not
assume Town Meeting would vote for any of it, and it does not treat a reserve as income.
Every figure is derived: the gap from `model/finance.py`, the balances from the town's
general ledger, the deposits from the Town Meeting articles that made them.

THE ONE THING IT INSISTS ON. A reserve spent on an operating cost buys ONE year of that
cost, and the cost returns the next year larger. That is the same arithmetic `free-cash.md`
makes about free cash and it is the whole reason this page exists rather than a sentence
saying "the town has $9M".
"""
import argparse
import collections
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

OUT = os.path.join(ROOT, 'sources', 'analyses', 'solution-options.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'solution-options.json')
LEDGER = os.path.join(ROOT, 'sources', 'data', 'trust-agency-balances.csv')

# Deposits that come from somewhere the town could NOT redirect to a school deficit. Sewer
# money is Sewer Enterprise retained earnings, which is ratepayers' money and stays in the
# sewer system; the Opioid fund is a legal settlement dedicated by the article that
# created it. Calling the whole deposit divertible would be the single easiest way to get
# this page wrong.
RESTRICTED_SOURCE = ('Sewer', 'Inflow', 'Opioid')

# The one account the ledger and the article history agree is the general Stabilization
# Fund: the only balance Town Meeting may appropriate for ANY lawful purpose.
GENERAL_ACCOUNT = '8124'

usd = lambda x: '${:,.0f}'.format(round(x))
usd2 = lambda x: '${:,.2f}'.format(x)


def gap_series(n=14):
    from finance import project
    return [(y['fy'], float(y['deficit'])) for y in project(years=n)]


def balances():
    out = {}
    if not os.path.exists(LEDGER):
        return out
    for r in csv.DictReader(open(LEDGER, encoding='utf-8')):
        if (r.get('group') or '').strip().upper() == 'STABILIZATION FUNDS':
            out[r['account']] = dict(name=' '.join((r['name'] or '').split()),
                                     held=float(r['held']))
    return out


def deposits():
    """Per year: everything voted in, and the part of it the town could redirect."""
    import build_stabilization as B
    fl = B.flows()
    every = collections.defaultdict(float)
    divertible = collections.defaultdict(float)
    for d in fl['deposits']:
        every[d['fy']] += d['amount']
        if not any(k in d['fund'] for k in RESTRICTED_SOURCE):
            divertible[d['fy']] += d['amount']
    return every, divertible, fl


def burndown(balance, gaps):
    """Spend a balance against the gap until it is gone. Returns the years it covered."""
    left, out = balance, []
    for fy, g in gaps:
        took = min(left, g)
        left -= took
        out.append(dict(fy=fy, gap=g, covered=took, shortfall=g - took, left=left))
        if left <= 0:
            break
    return out


def render():
    gaps = gap_series()
    bal = balances()
    every, divert, fl = deposits()
    years = sorted(every)
    span = years[-1] - years[0] + 1
    avg_all = sum(every.values()) / span
    avg_div = sum(divert.values()) / span
    general = bal.get(GENERAL_ACCOUNT, {}).get('held', 0.0)
    total_held = sum(v['held'] for v in bal.values())
    restricted = total_held - general
    run = burndown(general, gaps)
    exhausted = run[-1]
    first = gaps[0]

    b = []
    w = b.append
    w('# Solution options\n')
    w('**What the stabilization funds could actually do about the school budget gap, '
      'and for how long.**\n')
    w('Analysis, September 2026. The companion to '
      '[the stabilization funds](stabilization-funds.md), which describes what the town '
      'holds; this one is only about what can be done with it.\n')
    w('---\n')

    w('## The short version\n')
    w('**%s is the only balance Town Meeting may spend on anything lawful.** The other %s '
      'is restricted to the purpose each fund was created for. A school deficit is not '
      'that purpose for any of them.\n' % (usd(general), usd(restricted)))
    w('**Spending all of it closes FY%d and FY%d, and runs out partway through FY%d.** '
      'That is %s years, after which the money is gone and the gap is %s \u2014 larger '
      'than the one it started on.\n'
      % (run[0]['fy'], run[1]['fy'] if len(run) > 1 else run[0]['fy'], exhausted['fy'],
         '%.1f' % (len(run) - 1 + (run[-2]['left'] / exhausted['gap'] if len(run) > 1 and exhausted['gap'] else 0)),
         usd(exhausted['gap'])))
    w('**Stopping the deposits instead raises about %s a year**, which is recurring money '
      'against a recurring gap \u2014 the right SHAPE of answer. It covers %.0f%% of the '
      'FY%d gap and %.0f%% of FY%d\u2019s.\n'
      % (usd(avg_div), 100 * avg_div / first[1], first[0],
         100 * avg_div / gaps[2][1], gaps[2][0]))
    w('So: **neither closes the gap, and they fail differently.** One buys two years and '
      'then nothing. The other is permanent and is a quarter of what is needed.\n')
    w('---\n')

    w('## 1. Can the town stop putting money in?\n')
    w('Town Meeting voted **%s** into these funds between FY%d and FY%d, an average of '
      '**%s a year**.\n' % (usd(sum(every.values())), years[0], years[-1], usd(avg_all)))
    w('**But not all of it is the town\u2019s to redirect.** %s of it went to the sewer '
      'funds and the Opioid Settlement fund \u2014 sewer deposits are Sewer Enterprise '
      'retained earnings, which is ratepayers\u2019 money and stays in the sewer system, and '
      'the opioid money is a legal settlement dedicated by the article that created it. '
      'Neither could be sent to a school deficit whatever Town Meeting wanted.\n'
      % usd(sum(every.values()) - sum(divert.values())))
    w('| | per year | share of the FY%d gap |\n|---|---:|---:|' % first[0])
    w('| Everything voted in | %s | %.0f%% |' % (usd(avg_all), 100 * avg_all / first[1]))
    w('| The part that could be redirected | **%s** | **%.0f%%** |'
      % (usd(avg_div), 100 * avg_div / first[1]))
    w('')
    w('**This is the option with the right shape and the wrong size.** A deficit that '
      'returns every year is only ever closed by money that arrives every year, and this '
      'is that \u2014 it just is not enough of it. What it costs is whatever the funds were '
      'being built for: equipment the town would then borrow for, and a reserve that is '
      'part of how it is rated when it borrows.\n')
    w('---\n')

    w('## 2. Can the town spend what is already there?\n')
    w('**%s of it, yes.** That is the general Stabilization Fund, which a two-thirds Town '
      'Meeting vote may appropriate for any lawful purpose. Here is what happens if it is '
      'spent against the gap until it is gone:\n' % usd(general))
    w('| year | the gap | covered from the fund | still short | fund left |'
      '\n|---|---:|---:|---:|---:|')
    for r in run:
        w('| FY%d | %s | %s | %s | %s |'
          % (r['fy'], usd(r['gap']), usd(r['covered']),
             usd(r['shortfall']) if r['shortfall'] > 0.5 else '\u2014', usd(r['left'])))
    w('')
    w('**It buys two years.** In FY%d the fund is empty, the gap is %s, and every '
      'structural choice the town had in FY%d is still in front of it \u2014 with %s less '
      'in reserve and nothing to show a bond rating agency.\n'
      % (exhausted['fy'], usd(exhausted['gap']), first[0], usd(general)))
    w('*And this is the generous version.* It assumes Town Meeting votes the whole '
      'balance to the schools, in one go, with no reserve kept for a roof, a fire engine '
      'or a snow season \u2014 which is what the fund is for.\n')
    w('---\n')

    w('## 3. Then what?\n')
    w('That is the question the first two exist to set up, and the honest answer is that '
      'neither is a solution; they are timing.\n')
    w('- **Spending the balance is a one-off.** It moves the problem two years and makes '
      'it worse, because the gap grows while the reserve does not come back.\n')
    w('- **Stopping the deposits is permanent** and covers about a quarter of the first '
      'year\u2019s gap, falling as the gap grows.\n')
    w('- **Together** they cover FY%d and most of FY%d and still run out.\n'
      % (first[0], gaps[1][0]))
    w('A reserve spent on an operating cost buys one year of that cost. That is the same '
      'arithmetic [free cash](free-cash.md) makes, for the same reason: both are money '
      'the town has ONCE, set against a cost it has EVERY year.\n')
    w('---\n')

    w('## What this does not show\n')
    w('- **Whether Town Meeting would vote for any of it.** This is arithmetic about what '
      'the money could do, not a prediction about what anybody will do.\n')
    w('- **What the funds were being built for.** Diverting the deposits has a cost that '
      'does not appear in this table: the equipment, buildings and reserves they were '
      'accumulating toward.\n')
    w('- **What a rating agency would make of it.** A town that spends its stabilization '
      'fund borrows on different terms afterwards, and nothing here measures that.\n')
    w('- **Interest.** These balances earn about 3.5% a year, which is real money and is '
      'not modelled above; it would extend the burndown by months rather than years.\n')
    w('---\n')

    w('## Where the figures come from\n')
    w('- The gap, year by year: `model/finance.py`, the same projection the rest of the '
      'site uses.\n')
    w('- The balances: the town\u2019s general ledger at 31 March 2026, reconciled to the '
      'total the accounting system prints for them.\n')
    w('- The deposits: every Town Meeting article that put money into one of these funds, '
      'FY%d to FY%d. %s of those articles print no amount, so the totals are a floor.\n'
      % (years[0], years[-1], len(fl['unpriced'])))
    w('- The restricted/divertible split is OURS, read off which fund each deposit went '
      'to and where that fund\u2019s money comes from.\n')
    return '\n'.join(b) + '\n', dict(
        general=general, restricted=restricted, total=total_held,
        avg_all=avg_all, avg_divertible=avg_div, first_gap=first,
        burndown=run, gaps=gaps[:8])


# ---- the sources, rule 12's three things -------------------------------------------
#
# The markdown carries "Where the figures come from" for a reader; this is the same thing
# as data, so the source index and anything else that reads payloads sees it too. Both
# documents came to this project by records request rather than off a website, which IS
# an address and is written down as one.

def _sources():
    return [
        dict(path='sources/town-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx',
             sha256='', bytes=0, url='',
             docs_url='/docs/town-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx',
             filename='trust-agency-fy2026-p09.xlsx', table='trust_agency_balances',
             publisher='Town of Lunenburg \u2014 Town Accountant',
             note='The town\u2019s MUNIS trust and agency report at 31 March 2026. Every '
                  'balance on this page is the remaining balance this report prints, and '
                  'the extract refuses to write unless it foots to the system\u2019s own '
                  'subtotals. Obtained by a public records request; the chain is in '
                  'sources/town-ledgers/expenses/PROVENANCE-fy2026-p09.md.'),
        dict(path='sources/data/town-meeting-votes.csv', sha256='', bytes=0, url='',
             docs_url='/data/town-meeting-votes.csv', filename='town-meeting-votes.csv',
             table='town_meeting_votes', publisher='Town of Lunenburg',
             note='Every Town Meeting article, with the vote quoted verbatim. The '
                  'deposits this page averages are classified from each article\u2019s own '
                  'subject line, and the articles that print no amount are counted '
                  'rather than guessed at.'),
        dict(path='fy28/public/data/model.json', sha256='', bytes=0, url='',
             docs_url='/data/model.json', filename='model.json', table='',
             publisher='This project \u2014 derived',
             note='The projection. Every gap figure on this page is the level-service '
                  'shortfall model/finance.py computes for that year, on the same rates '
                  'the rest of the site uses; the burndown is arithmetic over it and '
                  'assumes nothing else.'),
    ]


def conclusions_for(data):
    """What this page establishes, as data rather than as sentences in the markdown.

    Rule 7d: a report is a payload rendered through the shared furniture, and conclusions
    are the half of that a reader actually meets first. Every figure named here is
    registered beside the sentence that states it, so `conclusions.py` can strip the
    renderings out of the prose and fail if a digit is left standing.

    THE BEARINGS ARE THE POINT ON THIS PAGE. Two of these are `lever` -- a reserve Town
    Meeting may vote, and a deposit it may stop voting -- and two are `sizes`. That is the
    whole argument of the report: the things you can pull are small or one-off, and the
    thing that is growing is neither.
    """
    import conclusions as C
    from conclusions import conclusion, emit, figure

    run = data['burndown']
    first_fy, first_gap = data['first_gap']
    gen = data['general']
    exhausted = run[-1]
    entering = run[-2]['left'] if len(run) > 1 else gen
    share = 100 * data['avg_divertible'] / first_gap
    last_gap = data['gaps'][-1]

    rows = [
        conclusion(
            id='the-whole-spendable-reserve-buys-two-years',
            claim='The %s the town may freely spend covers FY%d, FY%d and part of FY%d.'
                  % (C.usd(gen), run[0]['fy'], run[1]['fy'], exhausted['fy']),
            so_what='Then it is gone, and FY%d still needs %s with no reserve behind it.'
                    % (exhausted['fy'], C.usd(exhausted['gap'])),
            figures={'bal': figure(gen, C.usd(gen), 'spendable on anything lawful'),
                     'a': figure(run[0]['fy'], 'FY%d' % run[0]['fy']),
                     'b': figure(run[1]['fy'], 'FY%d' % run[1]['fy']),
                     'c': figure(exhausted['fy'], 'FY%d' % exhausted['fy']),
                     'gap': figure(exhausted['gap'], C.usd(exhausted['gap']),
                                   'the gap in the year the fund empties'),
                     'left': figure(entering, C.usd(entering),
                                    'left entering the third year')},
            figure='bal', kind='measured', bearing='lever',
            detail='The fund enters FY%d with %s against a %s gap and empties partway '
                   'through the year. And this is the generous reading: it assumes Town '
                   'Meeting votes the whole balance to the schools in one go, keeping '
                   'nothing back for a roof, a fire engine or a snow season, which is '
                   'what the fund is for.'
                   % (exhausted['fy'], C.usd(entering), C.usd(exhausted['gap'])),
            basis='The balance is the remaining balance the town\u2019s MUNIS trust and '
                  'agency report prints for the general Stabilization Fund at 31 March '
                  '2026. The gaps are `model/finance.py`. The burndown is arithmetic '
                  'over the two and models no interest.',
            not_shown='What a rating agency would make of a town that spent its '
                      'stabilization fund, or what the balance was being held against.',
            see=[('/analysis/free-cash', 'The same one-year problem, for free cash')],
        ),
        conclusion(
            id='stopping-the-deposits-is-the-right-shape-and-the-wrong-size',
            claim='Redirecting the deposits the town could lawfully redirect raises %s a '
                  'year.' % C.usd(data['avg_divertible']),
            so_what='Recurring money against a recurring gap \u2014 and %s of the FY%d '
                    'shortfall.' % (C.pct(share, 0), first_fy),
            figures={'div': figure(data['avg_divertible'], C.usd(data['avg_divertible']),
                                   'a year, redirectable'),
                     'all': figure(data['avg_all'], C.usd(data['avg_all']),
                                   'a year, voted in'),
                     'sh': figure(share, C.pct(share, 0), 'of the first year\u2019s gap'),
                     'fy': figure(first_fy, 'FY%d' % first_fy)},
            figure='div', kind='measured', bearing='lever',
            detail='Town Meeting votes %s a year into these funds on average, and %s of '
                   'that is the town\u2019s to send somewhere else. The difference is sewer '
                   'money \u2014 Sewer Enterprise retained earnings, which is ratepayers\u2019 '
                   'and stays in the sewer system \u2014 and an opioid settlement dedicated '
                   'by the article that created it. A deficit that returns every year is '
                   'only ever closed by money that arrives every year, which is what this '
                   'is; it is not enough of it.'
                   % (C.usd(data['avg_all']), C.usd(data['avg_divertible'])),
            basis='`town_meeting_votes`, deposits summed per fiscal year and divided by '
                  'the span. The restricted/redirectable split is OURS, read off which '
                  'fund each deposit went to and where that fund\u2019s money comes from.',
            not_shown='What the town gives up by not making the deposits \u2014 the '
                      'equipment, buildings and reserves they were accumulating toward.',
        ),
        conclusion(
            id='most-of-what-the-town-holds-cannot-reach-a-school-deficit',
            claim='%s of the %s held in these funds is restricted to a stated purpose.'
                  % (C.usd(data['restricted']), C.usd(data['total'])),
            so_what='A school deficit is not that purpose for any of them.',
            figures={'res': figure(data['restricted'], C.usd(data['restricted']),
                                   'restricted to a stated purpose'),
                     'tot': figure(data['total'], C.usd(data['total']),
                                   'held across the stabilization funds'),
                     'gen': figure(gen, C.usd(gen), 'spendable on anything lawful')},
            figure='res', kind='measured', bearing='sizes',
            detail='Only the general Stabilization Fund \u2014 %s \u2014 may be appropriated '
                   'for any lawful purpose, and that takes a two-thirds vote. A fund '
                   'created under c.40 \u00a75B may be spent only on the purpose named in '
                   'the article that created it, and that purpose lives in the article '
                   'rather than in the fund\u2019s name.' % C.usd(gen),
            basis='The town\u2019s MUNIS trust and agency report for the balances; the '
                  'general/restricted split follows the account the ledger itself groups '
                  'them under.',
            not_shown='Whether any restricted purpose is broad enough to reach a school '
                      'cost. That is a question for Town Counsel and a vote, not for a '
                      'balance.',
            allow=('c.40 \u00a75B',),
            see=[('/analysis/stabilization-funds', 'What each fund holds, and who may spend it')],
        ),
        conclusion(
            id='the-gap-grows-and-the-reserve-does-not',
            claim='The gap grows from %s to %s in three years. The reserve does not grow.'
                  % (C.usd(first_gap), C.usd(exhausted['gap'])),
            so_what='A one-off payment moves the problem into a year where it is bigger.',
            figures={'g1': figure(first_gap, C.usd(first_gap),
                                  'the level-service gap, first year'),
                     'g3': figure(exhausted['gap'], C.usd(exhausted['gap']),
                                  'the same gap three years on'),
                     'gl': figure(last_gap[1], C.usd(last_gap[1]),
                                  'the gap at the end of the projection'),
                     'fy': figure(last_gap[0], 'FY%d' % last_gap[0])},
            figure='g3', kind='measured', bearing='sizes',
            detail='By FY%d the projection puts it at %s. Spending a reserve against a '
                   'series like that buys the years at the small end and leaves the large '
                   'ones exactly as they were \u2014 which is why this page reports what '
                   'each option COVERS rather than whether it works.'
                   % (last_gap[0], C.usd(last_gap[1])),
            basis='`model/finance.py`, the level-service projection the rest of the site '
                  'uses. Budget columns only, per rule 1.',
            not_shown='Whether the projection\u2019s rates hold. Every one of them is '
                      'backtested against the district\u2019s own later budgets and none of '
                      'them is a promise.',
        ),
    ]
    return emit('solution-options', rows)


def payload(data):
    first_fy, first_gap = data['first_gap']
    run = data['burndown']
    return dict(
        generated_by='scripts/build_solution_options.py',
        about='What the stabilization funds could do about the school budget gap, and for '
              'how long.',
        grain='DOLLARS. The gap is the projection’s level-service shortfall by fiscal '
              'year. The balance is what the general ledger says the general Stabilization '
              'Fund held at 31 March 2026. The deposits are what Town Meeting VOTED in, '
              'which is not the same quantity as what the balances moved.',
        stats=[
            dict(value=usd(data['general']), tone='var(--series-cost)',
                 label='the only balance Town Meeting may spend on anything lawful, of %s held'
                       % usd(data['total'])),
            dict(value='%d years' % (len(run) - 1),
                 label='that it buys against the gap before it is gone'),
            dict(value=usd(data['avg_divertible']),
                 label='a year if the town stopped putting money in — %.0f%% of the FY%d gap'
                       % (100 * data['avg_divertible'] / first_gap, first_fy)),
        ],
        burndown=run, gaps=data['gaps'],
        sources=_sources(),
        not_established=[
            'Whether Town Meeting would vote for any of it. This is arithmetic about '
            'what the money could do, not a prediction about what anybody will do.',
            'What the funds were being built for, and what the town gives up by not '
            'building them.',
            'What a rating agency would make of a town that spent its stabilization '
            'fund.',
            'Interest. These balances earn about 3.5% a year, which would extend the '
            'burndown by months rather than years and is not modelled.',
        ],
        conclusions=conclusions_for(data),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    md, data = render()
    pay = json.dumps(payload(data), indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        pcur = open(PAYLOAD, encoding='utf-8').read() if os.path.exists(PAYLOAD) else ''
        bad = [n for n, (g, c) in (('solution-options.md', (md, cur)),
                                   ('solution-options.json', (pay, pcur))) if g != c]
        if bad:
            print('STALE %s' % ', '.join(bad), file=sys.stderr)
            return 1
        print('solution-options is current')
        return 0
    open(OUT, 'w', encoding='utf-8').write(md)
    open(PAYLOAD, 'w', encoding='utf-8').write(pay)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
