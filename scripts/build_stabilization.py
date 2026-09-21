#!/usr/bin/env python3
"""The town's stabilization funds: what they are, what is in them, and who may spend them.

    python3 scripts/build_stabilization.py           # write sources/analyses/stabilization-funds.md
    python3 scripts/build_stabilization.py --check

TJ, 20 September 2026: "what are these used for, how much is in them, how are they spent,
when are they spent, and can we use the money in those to pay for deficits like the
school, and if we lower the yearly investment can we do the same we explored for free
cash."

SIX QUESTIONS, AND THIS FILE ANSWERS TWO. The other four are series questions -- how a
balance moved, what was taken out, when, and what the town puts in each year -- and the
series does not exist yet in a form anything may aggregate. `report_trust_funds` holds 642
rows across FY2011-FY2025 of which twelve are reconciled to a total the document prints;
the stabilization balances below are FY2025 and carry `no check`.

So this report is deliberately short, says which questions it cannot answer, and points at
the plan that would. Publishing a trend off `check failed` rows would be the exact defect
this archive keeps catching -- see `notes/plans/STABILIZATION-FUNDS.md` and the
`extraction` rows in money-gaps.csv.

STABILIZATION IS NOT A TRUST FUND, THOUGH THE TOWN PRINTS THEM TOGETHER. The annual report
groups everything the Treasurer holds under one heading, which is the right axis for a
treasurer and the wrong one for every question above: those are about who may vote to
spend. A scholarship bequest and the town's own reserve sit in the same table and are not
the same instrument.
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
OUT = os.path.join(ROOT, 'sources', 'analyses', 'stabilization-funds.md')
PROVEN = os.path.join(ROOT, 'sources', 'data', 'stabilization-balances.csv')
FY = 2025

usd = lambda x: '${:,.2f}'.format(x)
# A DERIVED COUNT STILL READS AS A WORD. "3 funds, 3 different things happening" is
# correct and reads like a log line; spelling the small ones costs nothing and keeps the
# figure derived, which is the part rule 2 cares about.
WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
plural_articles = lambda n: ('%d articles' % n) if n != 1 else '1 article'
word = lambda n: WORDS[n] if 0 <= n < len(WORDS) else '{:,}'.format(n)
# The reader is already inside a section about stabilization funds, so a name ending in
# the word followed by the word again -- "the Zoning Incentive Stabilization fund" -- is
# the kind of repetition that reads as a machine wrote it. The full printed name is in
# the table; this is the running prose.
bare = lambda n: n[:-len(' Stabilization')] if n.endswith(' Stabilization') else n
usd0 = lambda x: '${:,.0f}'.format(x)

# WHICH FUND IS GENERAL AND WHICH IS RESTRICTED. This is the whole of question 5 and it is
# OURS, read off each fund's name rather than off a document that states the distinction --
# the annual report prints a balance and never says what may be spent on what. Marked as
# ours on the page for that reason. A special purpose stabilization fund is created for a
# stated purpose under c.40 s5B and may be spent only on it; the general fund may be
# appropriated for any lawful purpose.
GENERAL = {'8124'}


LEDGER = os.path.join(ROOT, 'sources', 'data', 'trust-agency-balances.csv')
LEDGER_AS_OF = '31 March 2026'
LEDGER_FY = 2026


def gather():
    """What each stabilization fund holds, FROM THE LEDGER.

    THIS USED TO READ A PHOTOGRAPH. `report_trust_funds` is the annual report's
    trust-fund table, read off a scan of the printed page, and for FY2025 it gave seven
    funds totalling $6,444,504 with no reconciliation behind it -- which is why the page
    carried a warning not to quote a balance.

    MUNIS prints the same thing and prints it better: nine accounts under its own
    `STABILIZATION FUNDS` subtotal, each with the year's revenue and expenditure beside
    it, and the subtotal ties to the rows. Rule 13a -- a sheet the accounting system
    printed is proof, a sheet somebody assembled is not, and a photograph of a printed
    table is neither.

    **The two agree to the cent where they overlap**, on all three funds that can be
    compared, which is the best evidence this project has that the table reader works.
    The annual-report series stays where it is used for HISTORY; this is what the funds
    hold now.
    """
    if not os.path.exists(LEDGER):
        raise SystemExit('missing %s -- run scripts/extract_trust_agency.py'
                         % os.path.relpath(LEDGER, ROOT))
    rows = []
    for r in csv.DictReader(open(LEDGER, encoding='utf-8')):
        if (r.get('group') or '').strip().upper() != 'STABILIZATION FUNDS':
            continue
        rows.append(dict(
            code=r['account'], name=' '.join((r['name'] or '').split()),
            amount=float(r['held']),
            revenue=-float(r['revenue']) if r['revenue'] else 0.0,
            expenditure=float(r['expenditure']) if r['expenditure'] else 0.0,
            remaining=-float(r['remaining']) if r['remaining'] else 0.0,
            status='ledger'))
    if not rows:
        raise SystemExit('no STABILIZATION FUNDS rows in %s'
                         % os.path.relpath(LEDGER, ROOT))
    rows.sort(key=lambda x: -x['amount'])
    return rows


def proven():
    """Balances read off the reports and verified against the tables' own arithmetic.

    A separate file from the FY2025 balances above and a different KIND of figure: these
    close on two identities the document states, so they are the only stabilization
    figures in this archive that anything has checked. See scripts/extract_stabilization.py
    and rule 13b.
    """
    if not os.path.exists(PROVEN):
        return []
    return list(csv.DictReader(open(PROVEN, encoding='utf-8')))


def creations():
    """The Town Meeting articles that created these funds, with what each is FOR.

    TJ, 20 September 2026, reading the report: "for 'what it may be used on' and 'its own
    stated purpose only', do we have the descriptions of those?"

    We did not. `fund-owners.csv` has a `purpose` and an `authority` column and both are
    empty for all nine stabilization funds, so the report asserted a restriction whose
    content it could not state -- the fund NAMES imply a purpose and a name is not the
    article that created the fund.

    The articles are in the archive: `town-meeting-votes.csv` carries 53 that mention
    stabilization, five of which create one, each with the town's own words and the
    statute quoted. That is the purpose and the authority, from the vote rather than from
    the label.
    """
    f = os.path.join(ROOT, 'sources', 'data', 'town-meeting-votes.csv')
    if not os.path.exists(f):
        return []
    out = []
    for r in csv.DictReader(open(f, encoding='utf-8')):
        both = (r.get('subject') or '') + ' ' + (r.get('quote') or '')
        if 'stabiliz' not in both.lower():
            continue
        if not re.search(r'\b(creat|establish)', both, re.I):
            continue
        out.append(dict(fy=r['fy'], meeting=r['meeting'], article=r['article'],
                        result=r['result'], subject=(r.get('subject') or '').strip(),
                        quote=' '.join((r.get('quote') or '').split())))
    return sorted(out, key=lambda r: r['fy'])


# WHICH FUND AN ARTICLE IS ABOUT, matched on the words the town uses in the article.
# OURS, and stated as ours: the votes file names funds in prose and carries no account
# code, so this is a reading of each article's subject rather than a join on anything.
FUND_WORDS = [
    ('reserve capacity', 'Sewer Reserve Capacity Stabilization'),
    # TWO FUNDS, NOT ONE NAME USED TWO WAYS -- and it took the town's own balance sheet to
    # settle it. The warrants say "Sewer Capital Reserve Stabilization Fund" and "Sewer
    # Reserve Capacity Stabilization Fund", sometimes both in one year for different
    # amounts, which reads like sloppy naming. FY2024's annual report lists them as
    # separate rows on separate pages -- `8132 Reserve Capacity Stabilization Fund` and
    # `Sewer Capital Reserve` -- and FY2023 article 14 transfers out of both in a single
    # motion, $35,000 from one and $20,962.40 from the other. Folding them together would
    # have merged two funds on a published page.
    ('capital reserve', 'Sewer Capital Reserve Stabilization'),
    ('inflow', 'Inflow/Infiltration Stabilization'),
    ('infiltration', 'Inflow/Infiltration Stabilization'),
    ('health insurance', 'Health Insurance Stabilization'),
    ('opioid', 'Opioid Settlement Stabilization'),
    ('town building', 'Town Building Stabilization'),
    ('vehicle', 'Vehicle/Equipment Stabilization'),
    ('zoning', 'Zoning Incentive Stabilization'),
    # LAST, AND IT WAS MISSING. Twelve articles name the SPECIAL PURPOSE Stabilization
    # Fund and every one of them was falling through to the general fund, because the
    # fallback is "an article naming no particular fund is the general one" and this list
    # had no word for it. That put $250,000 and $450,000 deposits, and the $986,000 voted
    # out for an ambulance, against the wrong fund on a published page. It is last so that
    # an article naming a specific sewer or opioid fund still matches that one first.
    ('special purpose', 'Special Purpose Stabilization'),
]


def history():
    """Every Town Meeting article that touches a stabilization fund, by fund and year.

    TJ: "can you also give the history of each of the funds if we have it? why it was
    created, when, which meetings, etc."

    53 articles across FY2011-FY2025, which is as far back as the town-meeting record in
    this archive reaches. An article that names no particular fund is the GENERAL
    Stabilization Fund, which is what the town means when it says "the Stabilization
    Fund" with no qualifier -- that is a reading and it is said out loud on the page.
    """
    f = os.path.join(ROOT, 'sources', 'data', 'town-meeting-votes.csv')
    if not os.path.exists(f):
        return {}
    by = {}
    for r in csv.DictReader(open(f, encoding='utf-8')):
        both = ((r.get('subject') or '') + ' ' + (r.get('quote') or '')).lower()
        if 'stabiliz' not in both:
            continue
        fund = next((label for word, label in FUND_WORDS if word in both),
                    'Stabilization Fund (general)')
        by.setdefault(fund, []).append(dict(
            fy=r['fy'], meeting=r['meeting'], date=r.get('meeting_date') or '',
            article=r['article'], result=r['result'],
            subject=' '.join((r.get('subject') or '').split()),
            amount=(r.get('amount_as_printed') or '').strip(),
            fincom=(r.get('fincom') or '').strip(),
            quote=' '.join((r.get('quote') or '').split())))
    for v in by.values():
        v.sort(key=lambda r: (r['fy'], r['article']))
    return by


# WHAT AN ARTICLE DOES, NOT WHICH FUND IT NAMES. `history()` answers "which fund is this
# about"; this answers "does money go IN or OUT", which is a different question and the
# one TJ's two questions turn on: can the town put LESS in each year, and can it take out
# what is already there.
#
# THE TRAP, AND IT IS EXPENSIVE. Of the 53 articles that mention a stabilization fund,
# five are sewer ENTERPRISE operating budgets -- $943,191.54, $1,213,182.00, $1,339,850.95
# and two amendments -- that mention a fund in passing in their quote. Summed as deposits
# they would overstate the total by $3.7M, more than the deposits themselves. So the
# classification reads the SUBJECT, which says what the article does, and everything it
# cannot place is counted separately and said out loud rather than folded into a total.
NOT_ABOUT = re.compile(r'^(operate|fund the sewer|appropriate funds to operate|amend)',
                       re.I)
# "to the X Stabilization Fund" or "into the X Stabilization Fund", and a creation that
# also puts money in.
# `^create` on its own, because the funding verb can sit on either side of the fund's
# name: "Create AND FUND a Health Insurance Stabilization Fund" puts it before, "Create an
# Inflow/Infiltration Stabilization Fund AND FUND IT" after. Requiring it after filed
# $369,951.10 of real deposits as unclassifiable. A creation article that prints an amount
# is putting that amount in -- and one that prints none (Town Building) still falls to
# `unpriced`, because the amount is what is missing, not the intent.
DEPOSIT = re.compile(r'\b(to|into)\b[^.]{0,45}stabiliz|^create\b[^.]{0,80}stabiliz',
                     re.I)
# Money leaving: "from the X Stabilization Fund", or "Transfer X Stabilization funds FOR
# <a thing>". The order below matters -- DEPOSIT is tested first, because "Transfer funds
# to the Special Purpose Stabilization Fund for future capital" is a deposit whose
# sentence happens to contain the word `for`, and testing this pattern first filed
# $200,000 of deposits as spending.
SPEND = re.compile(r'\bfrom the\b[^.]{0,40}stabiliz|stabilization funds?\s+for\b'
                   r'|\bsettlement funds?\s+for\b', re.I)


def money(s):
    s = (s or '').replace('$', '').replace(',', '').strip().rstrip('.')
    try:
        return float(s)
    except ValueError:
        return None


def withdrawals():
    """Every withdrawal the annual reports print, with the words around it.

    TJ: "we need to put 'What has come back out' in its own section, list the funds, the
    pull, the year, and list EVERYTHING we know about. peopel wnat to know what thos eare
    being used on and when."

    And TJ again, on where they live: "the statements of where the money was spent i think
    i saw in descriptive paragraphs in the town annual report, not in a table, right?" --
    which is exactly right and is why nothing found them for weeks. A withdrawal is a
    clause inside a warrant article about something else, in prose, and no table reader
    was ever going to see it.
    """
    f = os.path.join(ROOT, 'sources', 'data', 'stabilization-flows.csv')
    if not os.path.exists(f):
        return []
    return list(csv.DictReader(open(f, encoding='utf-8')))


def flows():
    """Town Meeting articles that put money into a stabilization fund, or take it out.

    Returns dict(deposits=[...], spends=[...], unpriced=[...], not_about=[...],
                 unclear=[...]) -- every one of the 53 articles lands in exactly one, so
    the buckets can be counted against the whole and nothing goes missing quietly.
    """
    f = os.path.join(ROOT, 'sources', 'data', 'town-meeting-votes.csv')
    out = dict(deposits=[], spends=[], unpriced=[], not_about=[], unclear=[])
    if not os.path.exists(f):
        return out
    for r in csv.DictReader(open(f, encoding='utf-8')):
        both = ((r.get('subject') or '') + ' ' + (r.get('quote') or '')).lower()
        if 'stabiliz' not in both:
            continue
        sub = ' '.join((r.get('subject') or '').split())
        amt = money(r.get('amount_as_printed'))
        # THE FUND COMES OFF THIS ROW'S OWN SUBJECT, NEVER OFF A JOIN. Keying articles on
        # (fy, article) collapses the annual and special Town Meeting -- both have an
        # article 8 -- and silently hands one article's subject to another: it reported
        # FY2018's $87,000 stabilization deposit as "fund a salary survey". Adding the
        # meeting type still leaves 18 colliding keys, because a year can hold two special
        # meetings. There is no join to fix, only a join to delete: the subject is already
        # on the row being classified.
        #
        # The QUOTE is deliberately not consulted here. It routinely names several funds
        # in one sentence, and matching against it attributed $121,362 of FY2023 deposits
        # to the Zoning Incentive fund, which received none.
        fund = next((lbl for word, lbl in FUND_WORDS if word in sub.lower()),
                    'Stabilization Fund (general)')
        row = dict(fy=int(r['fy']), article=r['article'], amount=amt, subject=sub,
                   fund=fund, meeting=r.get('meeting', ''), result=r.get('result', ''))
        if NOT_ABOUT.match(sub):
            out['not_about'].append(row)
        elif amt is None:
            out['unpriced'].append(row)
        elif DEPOSIT.search(sub):
            out['deposits'].append(row)
        elif SPEND.search(sub):
            out['spends'].append(row)
        else:
            out['unclear'].append(row)
    return out


def render(rows):
    total = sum(r['amount'] for r in rows)
    gen = [r for r in rows if r['code'] in GENERAL]
    spec = [r for r in rows if r['code'] not in GENERAL]
    gtot = sum(r['amount'] for r in gen)
    stot = sum(r['amount'] for r in spec)
    b = []; w = b.append
    # SECTION ORDER IS DECLARED, NOT IMPLIED BY WHERE THE CODE HAPPENS TO SIT.
    # TJ set it: charts first, then the other findings, what is in them, what goes in
    # each year, each fund year by year, then everything else as it was. Building the
    # sections in whatever order is convenient and then emitting them in THIS order means
    # a future reorder is one line here rather than a careful cut-and-paste through four
    # hundred lines of generator.
    marks = []
    mark = lambda name: marks.append((name, len(b)))
    # Needed by the short version, which now answers both of the questions a reader
    # actually arrives with rather than only the one about the balance.
    fl = flows()
    dep_total = sum(d['amount'] for d in fl['deposits'])
    w('# The stabilization funds, and who may spend them\n')
    w('**What the town holds in reserve, which of it could lawfully be spent on an '
      'operating deficit, and the four questions about it this archive cannot yet '
      'answer.**\n')
    # THE WARNING CAME OFF, BECAUSE THE FIGURES CHANGED SOURCE. It read "balances are
    # FY2025 and are not reconciled -- see the caveat before quoting one", which was the
    # right thing to say about seven figures read off a photograph of a printed table. The
    # balances are now the general ledger's, tied to the subtotal MUNIS prints for them,
    # so the honest sentence is the opposite one. Rule 3: say which numbers are ours, and
    # these are not.
    w('Analysis, September 2026. Balances are the town\u2019s own general ledger at %s, '
      'reconciled to the total the accounting system prints for them.\n' % LEDGER_AS_OF)
    mark('short')
    w('---\n')
    w('## The short version\n')
    # METRIC-LED, THE WAY THE OTHER REPORTS DO IT. TJ: "we should put metrics into the
    # short version the same as other reports." Rule 7b's shape -- the METRIC with its
    # unit, one line saying what it is, one line saying what follows -- and the hard part
    # is not the trimming: it is that each figure has to carry its own meaning, which is
    # why every one below has its unit and its denominator attached.
    w('**%s held, across the %d accounts the ledger groups as stabilization funds.** '
      'That is what the town has in reserve outside its operating budget \u2014 a '
      'balance, not an income, and two of the nine are a pension trust and a '
      'conservation fund rather than anything Town Meeting would call stabilization.\n'
      % (usd0(total), len(rows)))
    w('**%s of it can be spent on anything lawful** \u2014 the general Stabilization '
      'Fund, by a two-thirds Town Meeting vote. The other %s is restricted to the purpose '
      'each fund was created for, so it cannot be moved to a school deficit whatever '
      'Town Meeting thinks of the idea.\n' % (usd0(gtot), usd0(stot)))
    if dep_total:
        _by = {}
        for _d in fl['deposits']:
            _by[_d['fy']] = _by.get(_d['fy'], 0.0) + _d['amount']
        _lo, _hi = min(_by), max(_by)
        _span = _hi - _lo + 1
        _avg = dep_total / _span
        # THE RUN OF YEARS ABOVE THAT AVERAGE, DERIVED RATHER THAN CHOSEN. Naming a
        # window by hand is rule 2 wearing a date range: it would go on saying
        # "FY2018-FY2023" long after the data moved.
        _above = sorted(y for y in _by if _by[y] > _avg)
        _run, _best = [], []
        for y in _above:
            _run = _run + [y] if _run and y == _run[-1] + 1 else [y]
            if len(_run) > len(_best):
                _best = list(_run)
        w('**%s voted in since FY%d \u2014 an average of %s a year.** This is the money '
          'going IN, one Town Meeting article at a time, and it is the figure the '
          'cheaper question turns on. It is a FLOOR: %d of the articles print no amount.\n'
          % (usd0(dep_total), _lo, usd0(_avg), len(fl['unpriced'])))
        if len(_best) >= 3:
            w('**%s to %s a year in FY%d\u2013FY%d**, the %d straight years that ran above '
              'that average. Reducing a deposit is RECURRING money where spending a '
              'balance is a one-off \u2014 and a recurring gap is only ever closed by '
              'recurring money.\n'
              % (usd0(min(_by[y] for y in _best)), usd0(max(_by[y] for y in _best)),
                 _best[0], _best[-1], len(_best)))
    # FROM THE FLOWS DATASET, not the article subjects. The short version was still
    # quoting $1,066,000 from two articles whose SUBJECT is a withdrawal, while the
    # section below it lists eight found by reading the article TEXT. A page that
    # disagrees with itself between the summary and the table is worse than one that
    # under-reports.
    _wd = [r for r in withdrawals() if r['confidence'] == 'clear']
    if _wd:
        w('**%s has come back out**, across %d votes \u2014 and every one is a clause '
          'inside an article about something else, so this is a floor.\n'
          % (usd0(sum(float(r['amount']) for r in _wd)), len(_wd)))
    # THE DEFICIT ARGUMENT MOVED OUT. TJ: "the current stabilization page should be more
    # focused on info about the stabilization not necessarily focused on using it to
    # close the deficit." It kept drifting -- a description of nine funds that turned
    # into an argument about the schools every few paragraphs. Those are two documents
    # for two readers, and this one is the description. The arithmetic is now in
    # stabilization-option.md and this is a pointer rather than a summary of it, because a
    # summary here would drift back.
    w('*Whether any of this could close the school budget gap, and for how long, is a '
      'different question with a different answer.* It has its own report: '
      '[The stabilization option](stabilization-option.md).\n')

    # ---- WHAT GOES IN EACH YEAR. TJ's first question, and the one the balances alone
    # cannot answer: "can we reduce how much goes into each fund each year to pay for the
    # deficit?" That is a question about the ANNUAL DEPOSIT, not the balance, and the
    # deposit is a Town Meeting vote rather than anything the annual report prints.
    dep, spd = fl['deposits'], fl['spends']
    if dep:
        import collections as _c
        byfy = _c.defaultdict(float)
        for d in dep:
            byfy[d['fy']] += d['amount']
        # ONLY THE YEARS WHERE EVERY ARTICLE CARRIES A PRICE. Seven articles print no
        # amount -- including BOTH of FY2025's appropriations -- so a mean across all
        # years would report a collapse in deposits that is really a gap in what the
        # warrant printed.
        short_years = {r['fy'] for r in fl['unpriced']}
        full = sorted(y for y in byfy if y not in short_years)
        depd = sum(d['amount'] for d in dep)
        mark('goesin')
        w('---\n')
        w('## What goes in each year\n')
        w('Town Meeting has voted **%s into the stabilization funds** across %d articles, '
          'FY%d to FY%d \u2014 and **%s back out**, in %d articles.\n'
          % (usd0(depd), len(dep), min(byfy), max(byfy),
             usd0(sum(x['amount'] for x in spd)), len(spd)))
        if len(full) >= 3:
            lo, hi = min(byfy[y] for y in full), max(byfy[y] for y in full)
            mid = sorted(byfy[y] for y in full)
            med = (mid[len(mid) // 2] if len(mid) % 2 else
                   (mid[len(mid) // 2 - 1] + mid[len(mid) // 2]) / 2)
            w('In the %d years where every article carries a printed amount, the town '
              'voted in between **%s and %s a year, median %s**. That is the figure the '
              'first question turns on: it is recurring money, it is decided one article '
              'at a time at Town Meeting, and it is the same order of magnitude as the '
              'gap the schools are projecting.\n'
              % (len(full), usd0(lo), usd0(hi), usd0(med)))
        # WHICH FUND, BECAUSE THE QUESTION IS ABOUT EACH ONE. TJ: "can we reduce how
        # much goes into each fund each year." A single yearly total cannot be acted on;
        # a reader deciding what to stop needs to see that two funds take nearly all of
        # it and the rest are sewer housekeeping.
        byfund = _c.defaultdict(lambda: _c.defaultdict(float))
        for d in dep:
            byfund[d['fund']][d['fy']] += d['amount']
        ranked = sorted(byfund.items(), key=lambda kv: -sum(kv[1].values()))
        top2 = sum(sum(v.values()) for _, v in ranked[:2])
        # RANKED BY MONEY, AND THE SENTENCE MAY ONLY CLAIM MONEY. The first draft said
        # these were "the two with a repeating annual article", which is not what the
        # ranking measures and is not true: the Sewer Reserve Capacity fund appears in
        # more separate years than either of them, in much smaller amounts.
        w('**Two funds take most of it.** %s and %s together account for %s of the %s. '
          'They are where the first question bites \u2014 the rest is sewer '
          'housekeeping in amounts too small to close an operating gap.\n'
          % (ranked[0][0], ranked[1][0], usd0(top2), usd0(depd)))
        w('| fund | voted in, total | years | most recent |\n|---|---:|---:|---|')
        for fund, yrs in ranked:
            ys = sorted(yrs)
            w('| %s | %s | %d | FY%d, %s |'
              % (fund, usd0(sum(yrs.values())), len(ys), ys[-1], usd0(yrs[ys[-1]])))
        w('')
        w('| year | voted in | articles |\n|---|---:|---:|')
        for y in sorted(byfy):
            n = sum(1 for d in dep if d['fy'] == y)
            flag = '' if y not in short_years else ' \u2014 *understated*'
            w('| FY%d | %s%s | %d |' % (y, usd0(byfy[y]), flag, n))
        w('')
        # EVERY DEPOSIT, WITH THE ARTICLE THAT MADE IT. TJ: "can you list the the town
        # meeting articles (if we have them) and when the money got invested in each ...
        # we need the fund listed, the article it was added."
        w('**Every deposit we can price, and the article that made it.** A yearly total '
          'is a fact about the budget; this is the thing somebody can look up.\n')
        # THE MOTION, UNDER EACH DEPOSIT, CLOSED. TJ: "I wnt to read how these things get
        # approved and the public likely will too." The figures are the page and twenty
        # motions inline is a wall nobody reads, so each one is a disclosure -- the
        # ```quote fence that lib/markdown.tsx renders as a <details>. In the raw .md and
        # in the PDF it degrades to a labelled block, which is the right fallback.
        quotes = {}
        for r in csv.DictReader(open(os.path.join(
                ROOT, 'sources', 'data', 'town-meeting-votes.csv'), encoding='utf-8')):
            quotes[(int(r['fy']), r.get('meeting', ''), r['article'])] = \
                ' '.join((r.get('quote') or '').split())
        for d in sorted(dep, key=lambda r: (-r['fy'], -r['amount'])):
            w('**FY%d \u00b7 %s \u00b7 article %s \u2014 %s, %s**\n'
              % (d['fy'], (d.get('meeting') or 'Town Meeting').strip(), d['article'],
                 bare(d['fund']), usd(d['amount'])))
            q = quotes.get((d['fy'], d.get('meeting', ''), d['article']), '')
            if q:
                w('```quote what Town Meeting voted')
                w(q)
                w('```')
            else:
                w('*The warrant text for this article is not in the archive.*')
            w('')
        if fl['unpriced']:
            w('And %s the warrant records without an amount, so they are in none of the '
              'figures above:\n' % plural_articles(len(fl['unpriced'])))
            for u in sorted(fl['unpriced'], key=lambda r: -r['fy']):
                w('- FY%d, article %s \u2014 %s' % (u['fy'], u['article'], u['subject']))
            w('')
        w('*How solid is this.* Of the %d articles mentioning a stabilization fund, %d '
          'are deposits, %d are withdrawals, %d print no amount (marked *understated* '
          'above), and %d are sewer enterprise operating budgets that name a fund only '
          'in passing \u2014 those five total %s and counting them as deposits would '
          'overstate the money going in by more than the deposits themselves.\n'
          % (len(dep) + len(spd) + len(fl['unpriced']) + len(fl['not_about'])
             + len(fl['unclear']), len(dep), len(spd), len(fl['unpriced']),
             len(fl['not_about']),
             usd0(sum(x['amount'] for x in fl['not_about'] if x['amount']))))

    # ---- WHAT HAS COME BACK OUT, on its own ----------------------------------------
    mark('cameout')
    wd = withdrawals()
    if wd:
        clear = [r for r in wd if r['confidence'] == 'clear']
        flagged = [r for r in wd if r['confidence'] != 'clear']
        w('---\n')
        w('## What has come back out\n')
        w('**%s withdrawn, in %s the town printed.** Every one of these is a clause '
          'inside a Town Meeting article about something else \u2014 the sewer budget, an '
          'omnibus transfer \u2014 written in prose rather than set in any table, which is '
          'why a page built on the trust tables could not see them.\n'
          % (usd(sum(float(r['amount']) for r in clear)),
             plural_articles(len(clear)).replace('articles', 'separate votes')
             .replace('article', 'vote')))
        w('| year | fund | amount | what the article was for |\n|---|---|---:|---|')
        for r in sorted(clear, key=lambda r: (-int(r['fy']), -float(r['amount']))):
            purpose = r['quote']
            m = re.search(r'to\s+(operate|fund|purchase|pay)\b[^;]{0,70}', purpose, re.I)
            gist = m.group(0) if m else '\u2014 see the quote below'
            w('| FY%s | %s | %s | %s |'
              % (r['fy'], bare(r['fund']), usd(float(r['amount'])),
                 ' '.join(gist.split())[:64]))
        w('')
        w('**The words, because a withdrawal read out of prose has to be checkable.** '
          'These are the printed sentences, with the page they are on:\n')
        for r in sorted(clear, key=lambda r: (-int(r['fy']), -float(r['amount']))):
            w('- **FY%s, %s, %s** \u2014 page %s of that year\u2019s annual report:'
              % (r['fy'], bare(r['fund']), usd(float(r['amount'])), r['page']))
            w('  > %s' % r['quote'])
        w('')
        if flagged:
            w('**And %s this page will not add up**, because the printing does not let '
              'it. They are here rather than dropped:\n' % plural_articles(len(flagged)))
            for r in flagged:
                why = {'combined': 'the figure covers this fund AND another, and the '
                                   'article does not split it',
                       'maybe-duplicate': 'the same transaction appears in two '
                                          'consecutive reports, because each year\u2019s '
                                          'warrant recites the year before',
                       'deposit-misread': 'this is money going IN, matched by a pattern '
                                          'that cannot tell direction from wording alone'}
                w('- FY%s, %s, %s \u2014 %s'
                  % (r['fy'], bare(r['fund']), usd(float(r['amount'])),
                     why.get(r['confidence'], r['confidence'])))
            w('')
        w('*What this is not.* A complete account of what left these funds. It is what the '
          'annual reports PRINT, found by reading their article text; the ledger\u2019s own '
          'expenditure column would settle it and this archive holds one year of that.\n')

    mark('whatsin')
    w('---\n')
    w('## What is in them, at %s\n' % LEDGER_AS_OF)
    w('Straight from the town’s general ledger: what each account held at the start '
      'of FY%d, what has gone into it since, and what has come out. The account numbers '
      'are the town’s own.\n' % LEDGER_FY)
    w('| account | fund | held | in, this year | out, this year | may be spent on |'
      '\n|---|---|---:|---:|---:|---|')
    for r in rows:
        kind = ('**anything lawful**, by a 2/3 Town Meeting vote' if r['code'] in GENERAL
                else 'its own stated purpose only')
        w('| `%s` | %s | %s | %s | %s | %s |'
          % (r['code'], r['name'], usd(r['amount']),
             usd(r['revenue']) if r['revenue'] else '—',
             usd(r['expenditure']) if r['expenditure'] else '—', kind))
    w('| | **Total** | **%s** | **%s** | **%s** | |\n'
      % (usd(total), usd(sum(r['revenue'] for r in rows)),
         usd(sum(r['expenditure'] for r in rows))))
    w('**Two of these are not stabilization funds in the sense Town Meeting means, and '
      'they are here because the LEDGER files them here.** `8137 opeb` is the '
      'other-post-employment-benefits trust and `8125 conservation trust` is a '
      'conservation fund; together they are %s of the %s above. Quoting the total as '
      '“the stabilization funds” would be taking the accounting system’s '
      'filing decision for a statement about what may be spent — so the grouping is '
      'printed as the ledger prints it, and said out loud here.\n'
      % (usd(sum(r['amount'] for r in rows if r['code'] in ('8137', '8125'))),
         usd(total)))
    w('**The general/restricted split is ours**, read off each fund’s name and '
      'account. The ledger prints a balance and never says what may be spent on what.\n')
    # THE ROUTE, NOT THE PERSON. TJ: "we dont need to be so specific about where the data
    # came from on this page. listing Matt here isnt helpful." Right on both counts -- a
    # reader needs to know the figures came from the town's books by a records request
    # rather than off a website, and naming the private individual who filed it serves
    # nobody. The full chain stays in
    # sources/town-ledgers/expenses/PROVENANCE-fy2026-p09.md, which is what rule 12 asks
    # for; this is the page.
    w('**Where this came from.** The town\u2019s own general ledger, obtained by a public '
      'records request rather than published on a website. The report names its program, '
      'the moment it was generated and the Town Accountant who ran it. We hold it at one '
      'remove, so any note the town sent with the figures is not in this archive \u2014 '
      'and that matters here, because the equivalent package a few months later came with '
      'the Town Manager warning that figures were \u201clikely to continue to adjust as we '
      'continue the year-end reconciliation process\u201d.\n')
    w('**Nothing has come out of any of them so far this year.** Every expenditure '
      'column is empty at %s — a fact about nine months, not about whether these '
      'funds get spent. They do: the Health Insurance fund is a third of a million '
      'dollars lighter than the article that created it.\n' % LEDGER_AS_OF)
    # ---- THE TWO REFERENCE SECTIONS ARE BUILT HERE AND EMITTED LATER ----
    # TJ: "What has moved, so far as anything here can prove should be closer to the top.
    # The history of each fund and meetings should go closer to the bottom."
    #
    # Rule 7b, and the page had it backwards: what the funds have DONE is the conclusion,
    # and the creating votes and the 53 articles are the raw material behind it. A reader
    # was walking through eight subsections of Town Meeting minutes before reaching a
    # single figure about whether the money has grown. These two sections are captured
    # into `later` and re-emitted after the charts.
    mark('forwhat')
    # Hoisted above the creations block, which now reports which funds have NO creating
    # vote and needs the full fund list to do it.
    hist = history()
    cre = creations()
    if cre:
        w('---\n')
        w('## What each one is FOR, in the town\u2019s own words\n')
        # WHICH FUNDS HAVE A CREATING VOTE, AND WHICH DO NOT. TJ asked whether we hold
        # the minutes that justify setting up each of them. Listing the five we have and
        # staying silent about the rest answers a question nobody asked: the useful
        # sentence names the funds whose creating article is NOT in this archive, and
        # says why.
        def _fund_of(text):
            return next((lbl for word, lbl in FUND_WORDS if word in (text or '').lower()),
                        'Stabilization Fund (general)')

        have = {_fund_of(c['subject']) for c in cre}
        missing = [f for f in sorted(hist) if f not in have]
        w('A special purpose fund is restricted to the purpose it was created for, and '
          'that purpose lives in the article that created it \u2014 not in the '
          'fund\u2019s name. These are the creating votes this archive holds, each '
          'quoting **M.G.L. c.40 \u00a75B**, the statute that lets a town keep a '
          'stabilization fund at all.\n')
        w('**This archive holds a creating vote for %d of the %d funds that appear in the '
          'Town Meeting record, and not for %s.** The record here begins at FY2011 and '
          'those funds are older than it, so the article that created them \u2014 and the '
          'purpose that restricts them \u2014 is in a warrant nobody here has read. For a '
          'restricted fund that is the load-bearing document: without it, what the money '
          'may lawfully be spent on rests on the fund\u2019s NAME, which is a reading and '
          'not a rule.\n'
          % (len(have), len(hist), ', '.join(missing) if missing else 'none'))
        for c in cre:
            w('**%s** \u2014 FY%s %s Town Meeting, article %s, %s.\n'
              % (c['subject'], c['fy'], c['meeting'], c['article'],
                 c['result'].replace('_', ' ')))
            if c['quote']:
                w('> %s\n' % c['quote'][:300])
        w('**The three largest funds are not here, and that is the gap rather than an '
          'oversight.** The general Stabilization Fund, Vehicle/Equipment and Zoning '
          'Incentive were all created before FY2011, which is as far back as the '
          'town-meeting record in this archive reaches. Their purposes are known only '
          'from their names, and a name is not an article.\n')

    if hist:
        w('---\n')
        w('## Each fund, meeting by meeting\n')
        w('Every Town Meeting article this archive holds that touches a stabilization '
          'fund \u2014 what was asked, what was voted, and what the Finance Committee '
          'recommended. The record reaches back to FY2011 and no further, which is why '
          'three funds have no creation here.\n')
        w('**Which fund an article belongs to is OUR reading.** The votes name funds in '
          'prose and carry no account number, so an article saying only \u201cthe '
          'Stabilization Fund\u201d is taken as the general one \u2014 which is what '
          'the town means by it, and is still a reading.\n')
        for fund in sorted(hist, key=lambda k: -len(hist[k])):
            rs = hist[fund]
            w('### %s\n' % fund)
            w('%d article%s, FY%s to FY%s.\n'
              % (len(rs), '' if len(rs) == 1 else 's', rs[0]['fy'], rs[-1]['fy']))
            w('| year | meeting | art. | what was asked | amount | FinCom | result |')
            w('|---|---|---|---|---|---|---|')
            for r in rs:
                w('| FY%s | %s | %s | %s | %s | %s | %s |'
                  % (r['fy'], r['meeting'], r['article'], r['subject'][:76] or '\u2014',
                     r['amount'] or '\u2014', r['fincom'] or '\u2014',
                     r['result'].replace('_', ' ')))
            w('')
    mark('moved')
    w('---\n')
    pv = proven()
    if pv:
        gen = [r for r in pv if r['name'].strip().upper().startswith('STABILIZATION')
               and r['ending_market']]
        w('## What has moved, so far as anything here can prove\n')
        w('These are the only stabilization figures in this archive that have been '
          '**checked**. Each is read off a photograph of the town\u2019s own trust-fund '
          'table and then verified against identities the table states about every row '
          '\u2014 beginning plus activity equals ending cash, and, where the year prints '
          'a market value, ending cash plus unrealised equals ending market. A row that '
          'fails is not published.\n')
        w('Some years print no ending market value at all: FY2019\u2019s table carries the '
          'heading and not one figure under it. Those rows are proven on the cash '
          'identity alone, their market column is left empty rather than filled with the '
          'cash figure, and the basis column of the published CSV says which proof each '
          'row rests on.\n')
        if len(gen) >= 2:
            w('**The general Stabilization Fund**, the one Town Meeting may spend on '
              'anything lawful:\n')
            w('| | ending market value |\n|---|---:|')
            for r in sorted(gen, key=lambda r: r['fy']):
                w('| FY%s | %s |' % (r['fy'], usd(float(r['ending_market']))))
            w('')
            # NOT `a, b` -- `b` is the output list this function builds, and rebinding
            # it made render() return the CSV's field names instead of the report.
            ordered = sorted(gen, key=lambda r: r['fy'])
            first, last = ordered[0], ordered[-1]
            w('That is **%s more between FY%s and FY%s**, a rise of %.0f%%, in a fund '
              'whose purpose is to be available.\n'
              % (usd(float(last['ending_market']) - float(first['ending_market'])),
                 first['fy'], last['fy'],
                 (float(last['ending_market']) / float(first['ending_market']) - 1) * 100))
        # EACH FUND'S OWN SERIES, AND WHY IT IS THE STRONGEST THING HERE. Nothing was
        # built to check the extract across years, and it checks itself: the Zoning
        # Incentive fund runs FY2014 to FY2025 without a step, read off seven separate
        # annual reports by seven separate passes of the table reader. And FY2021's table
        # prints its BEGINNING market value as $2,041,061.72, which is exactly the ENDING
        # market value this extract proved from FY2020's report -- two independently read
        # documents agreeing on the balance where one year hands over to the next.
        def fund_key(r):
            # The bank is not part of the fund's name, and it moves: 8129 is printed
            # `(TD BANKNORTH)` in most years, `(TD BI` where the scan clipped it, and
            # `(TL 8129` where the account number ran into it. Cutting at the bracket
            # gives the fund, which is what a series is of. The stray account number is
            # dropped the same way it is elsewhere in this file.
            n = ' '.join(r['name'].split()).split('(')[0]
            return ' '.join(w for w in n.split() if not w.isdigit()).strip().title()

        series = collections.defaultdict(list)
        for r in pv:
            series[fund_key(r)].append(r)
        # THE LEDGER READING JOINS THE SERIES, because the charts plot it and a caption
        # computed from a different set of points than the picture above it is the page
        # arguing with itself. TJ, reading the chart: "we dont have data for the
        # stabilization fund beyond FY21?" -- we do, and it is the figure in this page's
        # own headline. MUNIS's opening balance at 2025-07-01 IS the FY2025 closing
        # balance, printed by the accounting system.
        #
        # Keyed on the ACCOUNT NUMBER: the ledger calls 8129 `playground fund` and the
        # annual report calls it `ZONING INCENTIVE STABILIZATION`, and the number is the
        # only identity both documents share. Only funds that already have a series get a
        # point, so nothing new appears and nothing is invented.
        LEDGER_SERIES = {'8124': 'Stabilization',
                         '8136': 'Vehicle/Equipment Stabilization',
                         '8129': 'Zoning Incentive Stabilization'}
        # The annual report's own per-account listing, for the years that print it. It
        # reaches funds and years the other-banks tables never did, and every figure in
        # it that can be checked against the ledger has agreed to the cent.
        listing = os.path.join(ROOT, 'sources', 'data', 'trust-fund-balances.csv')
        if os.path.exists(listing):
            for r in csv.DictReader(open(listing, encoding='utf-8')):
                label = LEDGER_SERIES.get(r['account'])
                if not label or label not in series or not r.get('balance'):
                    continue
                if any(x['fy'] == r['fy'] for x in series[label]):
                    continue
                series[label].append(dict(
                    fy=r['fy'], code=r['account'], name=label,
                    ending_cash=r['balance'], ending_market='',
                    basis='the annual report\u2019s trust fund balance listing',
                    page=r['page'], document=r['document']))
        # The Treasurer's Cash page, last and only where nothing else reaches. It is cash
        # held by a custodian rather than a fund balance -- for these funds the two have
        # matched to the cent wherever both exist, but that is a fact about funds held
        # whole in one place, not a rule, so it fills gaps and never overrides a balance.
        cash = os.path.join(ROOT, 'sources', 'data', 'treasurers-cash.csv')
        CASH_FOR = ((re.compile(r'bartholomew\s+stabilization\s+fund', re.I),
                     'Stabilization'),
                    (re.compile(r'vehicle/equipment\s+stabilization', re.I),
                     'Vehicle/Equipment Stabilization'),
                    (re.compile(r'zoning\s+(incentive\s+)?stabilization', re.I),
                     'Zoning Incentive Stabilization'))
        if os.path.exists(cash):
            for r in csv.DictReader(open(cash, encoding='utf-8')):
                label = next((l for pat, l in CASH_FOR
                              if pat.search(r['held_as'] or '')), None)
                if not label or label not in series:
                    continue
                if any(x['fy'] == r['fy'] for x in series[label]):
                    continue
                series[label].append(dict(
                    fy=r['fy'], code='', name=label, ending_cash=r['amount'],
                    ending_market='',
                    basis='the Treasurer\u2019s Cash page (cash held, not a fund balance)',
                    page=r['page'], document=r['document']))
        for r in rows:
            label = LEDGER_SERIES.get(r['code'])
            if not label or label not in series:
                continue
            fy = str(LEDGER_FY - 1)
            if any(x['fy'] == fy for x in series[label]):
                continue
            series[label].append(dict(
                fy=fy, code=r['code'], name=label, ending_cash='%.2f' % r['amount'],
                ending_market='', basis='the town\u2019s general ledger',
                page='', document='sources/town-ledgers/fund-balances/'
                                  'trust-agency-fy2026-p09.xlsx'))
        runs = {k: sorted(v, key=lambda r: int(r['fy']))
                for k, v in series.items() if len(v) >= 3}
        # THE CHARTS GO HERE, ABOVE THE FIGURES THEY DRAW. Three of them, and each
        # answers a question the other two cannot: how the funds compare in SIZE, what
        # shape each one has on its OWN scale, and how fast each moved. Drawn by
        # scripts/build_stabilization_charts.py from this same CSV, so they cannot drift
        # from the table underneath them.
        #
        # EVERY FIGURE IN THIS BLOCK IS DERIVED, INCLUDING THE ONES IN THE ALT TEXT. The
        # first draft typed "40.8% a year" and "$21,858 in eleven years" into the prose,
        # which is rule 2 exactly: the extraction is under active improvement, so those
        # sentences would have gone quietly wrong the next time a year started proving.
        # Alt text is prose that ships, the same as any other.
        chart_dir = os.path.join(ROOT, 'sources', 'analyses', 'charts')
        if runs and os.path.exists(os.path.join(chart_dir, 'stabilization-all.svg')):
            def rate(v):
                n = int(v[-1]['fy']) - int(v[0]['fy'])
                a0, a1 = float(v[0]['ending_cash']), float(v[-1]['ending_cash'])
                return ((a1 / a0) ** (1.0 / n) - 1) * 100 if n and a0 else 0.0

            def span(v):
                return int(v[-1]['fy']) - int(v[0]['fy'])

            ranked = sorted(runs.items(), key=lambda kv: -rate(kv[1]))
            fastest, slowest = ranked[0], ranked[-1]
            biggest = max(float(v[-1]['ending_cash']) for v in runs.values())
            allyears = sorted(int(r['fy']) for v in runs.values() for r in v)
            movers = ', '.join(
                '%s %.1f%% a year over %d years' % (bare(k), rate(v), span(v))
                for k, v in ranked)
            w('![%s on one scale, FY%d to FY%d. The tallest reaches %s by its last '
              'proven year; %s is a flat line near the axis the whole way. Dashed '
              'segments span years this archive has not yet proven.]'
              '(charts/stabilization-all.svg)\n'
              % ('%s stabilization fund%s' % (word(len(runs)).title(),
                                               '' if len(runs) == 1 else 's'),
                 allyears[0], allyears[-1], usd(biggest), bare(slowest[0])))
            w('On one scale the %s fund looks like nothing is happening to it. That is '
              'the finding, not a rendering problem \u2014 but it hides the shape, so '
              'each fund also gets its own panel:\n' % bare(slowest[0]))
            w('![The same %s funds, each panel stretched to its own range, so the '
              'shapes are comparable and the heights are not.]'
              '(charts/stabilization-each.svg)\n' % word(len(runs)))
            w('![How fast each fund moved per year between its first and last proven '
              'year: %s.](charts/stabilization-growth.svg)\n' % movers)
            if os.path.exists(os.path.join(chart_dir, 'stabilization-flows.svg')):
                w('And both directions at once \u2014 how often these funds are drawn on, '
                  'and for how much:\n')
                w('![Money voted into the stabilization funds each year, above the line, '
                  'against money taken back out, below it. Withdrawals are rare and '
                  'small beside the deposits.](charts/stabilization-flows.svg)\n')
            moved = (float(slowest[1][-1]['ending_cash'])
                     - float(slowest[1][0]['ending_cash']))
            w('**%s funds, %s different things happening.** The %s fund moved %s a year '
              'and the %s fund %s a year \u2014 those are being BUILT, and the Town '
              'Meeting articles listed earlier on this page are the votes that did it. '
              'The %s fund is not: it moved %s in %d years, which is what a balance does '
              'when it is left alone.\n'
              % (word(len(runs)).title(), word(len(runs)), bare(fastest[0]),
                 '%.1f%%' % rate(fastest[1]), bare(ranked[1][0]),
                 '%.1f%%' % rate(ranked[1][1]), bare(slowest[0]),
                 usd(moved), span(slowest[1])))
            w('*What the charts do not show.* A balance rising does not say how much of '
              'the rise is money voted in and how much is interest earned, and nothing '
              'in this data separates them. It also does not say a fund is AVAILABLE: '
              'what each may be spent on is the section above, and a balance is not a '
              'permission.\n')
        w('---\n')
        mark('byyear')
        if runs:
            w('## Each fund, year by year\n')
            w('Each figure below is its own reading, and they come from four places: '
              'the trust tables in the annual reports, checked against each page\u2019s '
              'own arithmetic; the per-account **Trust Fund Balance Detail** listing '
              'those reports print from FY2024; the **Treasurer\u2019s Cash** page, which '
              'every report prints and which is the only one of the four carrying the '
              'general Stabilization Fund; and the town\u2019s general ledger. **Every '
              'figure covered by more than one of them has agreed to the cent.**\n')
            w('*One of the four has a different grain.* The Treasurer\u2019s Cash page '
              'counts cash held by a custodian, not a fund balance \u2014 the Opioid fund '
              'shows $233,317.54 of cash at Bartholomew where the ledger puts the fund '
              'at $241,421.18. For the funds charted here the two have matched wherever '
              'both exist, because those funds sit whole in one place, but that is a '
              'fact about them and not a rule. It fills years nothing else reaches and '
              'never overrides a balance.\n')
            for k, v in sorted(runs.items(), key=lambda kv: -len(kv[1])):
                w('- **%s** \u2014 %s' % (k, ', '.join(
                    'FY%s %s' % (r['fy'], usd(float(r['ending_cash']))) for r in v)))
            w('')
        w('Every proven row:\n')
        # ENDING CASH IS THE COLUMN THAT IS ALWAYS PROVEN, so it leads. The market
        # value is the one that sometimes is not printed, and an em dash there means the
        # page printed none -- never that the fund held nothing.
        w('| year | account | fund | ending cash | ending market |\n|---|---|---|---:|---:|')
        for r in sorted(pv, key=lambda r: (r['fy'], r['name'])):
            w('| FY%s | `%s` | %s | %s | %s |'
              % (r['fy'], r['code'] or '\u2014', ' '.join(r['name'].split())[:44],
                 usd(float(r['ending_cash'])),
                 usd(float(r['ending_market'])) if r['ending_market'] else '\u2014'))
        w('')
        # HOW MUCH OF THE GRID IS EMPTY, because a reader looking at three lines cannot
        # tell whether that is three funds or all of them. TJ, reading the chart: "looks
        # like we are missing a lot of years ... can you tell me what we have for years
        # for each stabilization fund". Nine funds exist and six of them are a single
        # dot.
        n_funds = len(rows)
        n_years = LEDGER_FY - 1 - 2010
        cells = sum(len(v) for v in runs.values()) + max(0, n_funds - len(runs))
        w('**Nine funds, fifteen years, and most of the grid is empty.** Only %d of the '
          '%d funds have any history at all; the other %d are known from one reading, '
          'the ledger\u2019s. Across FY2011 to FY%d that is about %d of %d possible '
          'fund-years.\n'
          % (len(runs), n_funds, n_funds - len(runs), LEDGER_FY - 1, cells,
             n_funds * n_years))
        # THE BOTTLENECK IS THE READER, NOT THE RECORD, and the page implied the
        # opposite for weeks. "Those pages have not yet yielded a row whose arithmetic
        # closes" is true and reads as "the town did not publish it". TJ, 20 September
        # 2026: "i can almost guarantee you this data is all in the annual town report.
        # you prob missed it." He is right, and it is measurable -- about 154 fund rows
        # are visible in the OCR of twelve annual reports against 15 published here.
        w('**%d of those readings are proved, across %d years \u2014 and that is a limit of '
          'OUR reading, not of the town\u2019s record.** The annual reports print the '
          'whole trust and stabilization table every year, every fund, and roughly ten '
          'times as many fund rows are visible in our scans of them as this page '
          'publishes. A row appears here only where the page\u2019s own arithmetic closes '
          'on it, because publishing one that does not would be worse than publishing '
          'nothing \u2014 so the empty cells are a queue of work, not an absence of '
          'evidence.\n' % (len(pv), len({r['fy'] for r in pv})))
        w('Two things would empty that queue, and they are not alternatives. A better '
          'reader gets the figures the town has already printed. The MUNIS trust report '
          'for earlier years would get them from the accounting system instead, with '
          'revenue and expenditure beside every balance \u2014 which the annual report '
          'tables do not carry at all.\n')
        w('---\n')

    mark('cannot')
    w('---\n')
    w('## What this cannot answer yet, and why\n')
    w('Four of the six questions this report was asked are about MOVEMENT, and the series '
      'does not exist in a form anything may aggregate:\n')
    w('| question | blocked on |\n|---|---|')
    w('| How has each balance moved? | the series |')
    w('| How are they spent? | the disbursement columns, and the articles authorising '
      'each transfer out |')
    w('| When are they spent? | the same series, read as a pattern |')
    w('| If the town put less in each year, could that go to the gap? | the '
      'transfer-IN series, and separating OPEB from it |')
    w('')
    w('`report_trust_funds` holds 642 rows for FY2011–FY%d. **Twelve are reconciled '
      'to a total the document itself prints.** The balances above are `no check`: '
      'extracted, never tied to the page’s own total. Every page was surveyed before '
      'anyone tried — ten of seventeen years need real PDF geometry rather than text, '
      'because of mirrored layouts, rows offset from their own names, and column counts '
      'that change between years.\n' % FY)
    w('That is registered as a gap rather than left here: see the `extraction` rows in '
      '`sources/data/money-gaps.csv`, published at `/what-we-cannot-answer`. The work to '
      'close it is `notes/plans/STABILIZATION-FUNDS.md`.\n')
    mark('notshow')
    w('---\n')
    w('## What this does not show\n')
    w('- **That the balances are right.** They are unreconciled. A figure here is a place '
      'to look in the annual report, not a figure to quote at a meeting.\n')
    w('- **That the restricted funds are unavailable for ever.** Town Meeting created each '
      'one and can, in principle, act on them again. What it cannot do is spend a special '
      'purpose fund on something else while it stands.\n')
    w('- **That spending a reserve solves anything.** It is one-time money against a '
      'recurring cost — the same shape as the September Town Meeting appropriation '
      'that left %s of salary in the following year with nothing behind it.\n'
      % '$392,264')
    w('- **Why any balance is the size it is.** A balance is a fact; a reason is a '
      'hypothesis.\n')
    mark('sources')
    w('---\n')
    w('## Sources\n')
    w('| | |\n|---|---|')
    w('| Balances | `report_trust_funds`, from the annual town reports — status '
      '`no check` |')
    w('| The general/restricted split | ours, from each fund’s name |')
    w('| What the archive cannot yet say | `sources/data/money-gaps.csv`, side '
      '`extraction` |')
    # ---- EMIT IN THE DECLARED ORDER ----------------------------------------------
    # TJ, 20 September 2026: "all charts first. 'The other findings', What is in them,
    # FY2025, What goes in each year, 'Each fund, year by year' (as a new section) (then
    # the rest of whats already there in the same order)."
    #
    # `The other findings` is not in this list because it is not in this document: it is
    # the conclusions beyond the first three, rendered by Analysis.tsx from the payload,
    # and it lands directly after the first section of the fold -- which is why the charts
    # have to be that first section.
    ORDER = ['short', 'moved', 'whatsin', 'goesin', 'cameout', 'byyear', 'forwhat',
             'cannot', 'notshow', 'sources']
    head = b[:marks[0][1]] if marks else list(b)
    cut = {name: (start, marks[i + 1][1] if i + 1 < len(marks) else len(b))
           for i, (name, start) in enumerate(marks)}
    missing = [n for n in cut if n not in ORDER]
    if missing:
        raise SystemExit('section(s) built but never emitted: %s' % ', '.join(missing))
    out = list(head)
    for name in ORDER:
        if name in cut:
            lo, hi = cut[name]
            out.extend(b[lo:hi])
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = gather()
    out = render(rows)
    # BOTH OUTPUTS, FROM ONE PASS OVER ONE SET OF FIGURES. The page renders the payload;
    # the markdown is what /docs serves, what the PDF is made from, and what an agent
    # that cannot run JavaScript reads. Generating them separately is how the two would
    # come to disagree.
    pay = json.dumps(payload(rows), indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        pcur = open(PAYLOAD, encoding='utf-8').read() if os.path.exists(PAYLOAD) else ''
        bad = [n for n, (g, c) in (('stabilization-funds.md', (out, cur)),
                                   ('stabilization.json', (pay, pcur))) if g != c]
        if bad:
            print('STALE %s' % ', '.join(bad), file=sys.stderr); return 1
        print('stabilization-funds.md and stabilization.json are current'); return 0
    open(OUT, 'w', encoding='utf-8').write(out)
    open(PAYLOAD, 'w', encoding='utf-8').write(pay)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT),
                               os.path.relpath(PAYLOAD, ROOT))); return 0


# ============================================================================
# THE PAYLOAD. This report is becoming a model-driven page like every other one.
#
# TJ, 20 September 2026, after asking why the metrics here did not look like the metrics
# on the other reports: "this neeeds to be model driven ... is this written and built the
# same way the other pages are?" It was not. Twenty analyses are markdown rendered
# generically by Analysis.tsx, which has no way to show a Stat row or an Insight card,
# while twenty-nine reports are a generated JSON payload rendered through the shared
# furniture in components/report.tsx. Two kinds of report, and a reader takes a difference
# in PRESENTATION for a difference in CONFIDENCE -- which is the exact thing report.tsx
# was written to stop.
#
# So the same figures this file already computes for the markdown are emitted as a
# payload. The markdown stays: it is what /docs serves, what the PDF renders from, and
# what an agent that cannot run JavaScript reads.
# ============================================================================

# NAMED FOR THE REPORT'S OWN ID, because that is the whole contract. Analysis.tsx fetches
# `/data/<id>.json` for whatever report it is showing, and a payload under any other name
# is simply a report with no payload -- which is silent by design, since most analyses do
# not have one yet. It cost a build to find: `stabilization.json` against an id of
# `stabilization-funds` 404s, the page renders exactly as it did before, and nothing
# anywhere says why.
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'stabilization-funds.json')
MANIFEST_CSV = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')


def _sources():
    """The annual report the balances are read off, and the votes file behind the flows."""
    out = []
    try:
        with open(MANIFEST_CSV, encoding='utf-8') as fh:
            rows = {r['key']: r for r in csv.DictReader(fh)}
    except OSError:
        rows = {}
    key = next((k for k in rows if re.search(r'fy-%d-annual-town-report\.pdf$' % FY, k)),
               None)
    if key:
        r = rows[key]
        out.append(dict(
            path='sources/' + key, sha256=r.get('sha256', ''),
            bytes=int(r.get('bytes') or 0), url=r.get('upstream', ''),
            docs_url='/docs/' + key, filename=key.split('/')[-1],
            table='stabilization_balances', publisher='Town of Lunenburg',
            note='The annual town report. The trust and stabilization balances are a '
                 'photographed table inside it, read by scripts/read_trust_table.py and '
                 'published only where the page’s own arithmetic closes.'))
    # THE LEDGER, AND ITS ADDRESS. This is where the balances on this page come from, so
    # rule 12's three things travel with it. The route was a recorded GAP until TJ
    # supplied it: a public records request to the Town Manager,
    # answered before 14 August 2026, sent to this project directly. Two parts of it are
    # worth keeping in the published note rather than only in the provenance file -- the
    # request date is BOUNDED rather than known, and we are one remove from the town, so
    # any caveat the town sent with the figures is not in this archive.
    out.append(dict(
        path='sources/town-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx',
        sha256='', bytes=0, url='',
        docs_url='/docs/town-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx',
        filename='trust-agency-fy2026-p09.xlsx', table='trust_agency_balances',
        publisher='Town of Lunenburg — Town Accountant',
        note='The town’s MUNIS trust and agency report at 31 March 2026: every fund’s '
             'beginning balance, revenue, expenditure and remaining balance, with the '
             'system’s own subtotals. Obtained by a public records request rather than '
             'published on a website, and held at one remove from the town. The full '
             'chain \u2014 who asked, when, and what is bounded rather than known \u2014 is '
             'in sources/town-ledgers/expenses/PROVENANCE-fy2026-p09.md.'))
    out.append(dict(
        path='sources/data/town-meeting-votes.csv', sha256='', bytes=0, url='',
        docs_url='/data/town-meeting-votes.csv', filename='town-meeting-votes.csv',
        table='town_meeting_votes', publisher='Town of Lunenburg',
        note='Every Town Meeting article, with the vote quoted verbatim. The deposits and '
             'withdrawals on this page are classified from each article’s own '
             'subject line.'))
    return out


def payload(rows):
    import conclusions as C
    from conclusions import conclusion, emit, figure

    total = sum(r['amount'] for r in rows)
    gtot = sum(r['amount'] for r in rows if r['code'] in GENERAL)
    stot = total - gtot
    fl = flows()
    dep, spd = fl['deposits'], fl['spends']
    dep_total = sum(d['amount'] for d in dep)
    spd_total = sum(d['amount'] for d in spd)

    byfy = {}
    for d in dep:
        byfy[d['fy']] = byfy.get(d['fy'], 0.0) + d['amount']
    lo, hi = min(byfy), max(byfy)
    span = hi - lo + 1
    avg = dep_total / span
    short_years = {r['fy'] for r in fl['unpriced']}

    # The longest run of consecutive years above that average, derived rather than
    # chosen -- naming a window by hand is rule 2 wearing a date range.
    run, best = [], []
    for y in sorted(y for y in byfy if byfy[y] > avg):
        run = run + [y] if run and y == run[-1] + 1 else [y]
        if len(run) > len(best):
            best = list(run)

    byfund = {}
    for d in dep:
        byfund.setdefault(d['fund'], {})[d['fy']] = \
            byfund.setdefault(d['fund'], {}).get(d['fy'], 0.0) + d['amount']
    funds_ranked = sorted(byfund.items(), key=lambda kv: -sum(kv[1].values()))

    pv = proven()
    series = {}
    for r in pv:
        n = ' '.join(r['name'].split()).split('(')[0]
        n = ' '.join(w for w in n.split() if not w.isdigit()).strip().title()
        series.setdefault(n, []).append(
            dict(fy=int(r['fy']), ending_cash=float(r['ending_cash']),
                 ending_market=float(r['ending_market']) if r['ending_market'] else None,
                 basis=r['basis'], page=int(r['page'])))
    series = {k: sorted(v, key=lambda x: x['fy']) for k, v in series.items()
              if len(v) >= 3}

    hist = history()
    cre = creations()

    def _fund_of(t):
        return next((lbl for word, lbl in FUND_WORDS if word in (t or '').lower()),
                    'Stabilization Fund (general)')

    have = {_fund_of(c['subject']) for c in cre}
    missing = [f for f in sorted(hist) if f not in have]

    rank = sorted(series.items(), key=lambda kv: -_rate(kv[1]))
    fastest, slowest = (rank[0], rank[-1]) if rank else (None, None)

    rws = [
        conclusion(
            id='most-of-the-reserve-cannot-be-spent-on-an-operating-deficit',
            claim='Only %s of the %s reserve may be spent on anything lawful.'
                  % (C.usd(gtot), C.usd(total)),
            so_what='The other %s is restricted to the purpose each fund was created '
                    'for.' % C.usd(stot),
            figures={'held': figure(total, C.usd(total), 'held in reserve, FY%d' % FY),
                     'gen': figure(gtot, C.usd(gtot), 'spendable on anything lawful'),
                     'res': figure(stot, C.usd(stot), 'restricted to a stated purpose'),
                     'n': figure(len(rows), C.num(len(rows)), 'stabilization funds')},
            figure='gen', kind='measured', bearing='sizes',
            detail='The general fund takes a two-thirds Town Meeting vote. A special '
                   'purpose fund created under c.40 §5B may be spent only on its '
                   'stated purpose, and that purpose lives in the article that created '
                   'it rather than in the fund’s name.',
            basis='`stabilization_balances` for the balances; the general/restricted '
                  'split is OURS, read off each fund’s name because the annual '
                  'report prints a balance and never says what may be spent on what.',
            not_shown='Whether a restricted fund’s stated purpose is narrow or '
                      'broad. For four funds the creating article is not in this '
                      'archive at all.',
            allow=('c.40 \u00a75B',),
            see=[('/analysis/free-cash', 'The same one-year problem, for free cash')],
        ),
        conclusion(
            id='the-recurring-question-is-the-deposit-not-the-balance',
            claim='Town Meeting votes an average of %s a year into these funds.'
                  % C.usd(avg),
            so_what='Reducing a deposit is recurring money; spending a balance buys one '
                    'year.',
            figures={'in': figure(dep_total, C.usd(dep_total),
                                  'voted in since FY%d' % lo),
                     'avg': figure(avg, C.usd(avg), 'a year, on average'),
                     'fy': figure(lo, 'FY%d' % lo),
                     'last': figure(FY, 'FY%d' % FY),
                     'out': figure(spd_total, C.usd(spd_total), 'voted back out'),
                     'unp': figure(len(fl['unpriced']), C.num(len(fl['unpriced'])),
                                   'articles print no amount')},
            figure='avg', kind='measured', bearing='lever',
            detail='%s in total since FY%d, and it is a FLOOR: %s of the articles '
                   'print no amount, including both of FY%d’s appropriations. %s has '
                   'been voted back out, and that is a floor too — money also leaves '
                   'inside articles about something else.'
                   % (C.usd(dep_total), lo, C.num(len(fl['unpriced'])), FY,
                      C.usd(spd_total)),
            basis='`town_meeting_votes`, classified from each article’s own subject '
                  'line. Five sewer enterprise operating budgets mention a fund in '
                  'passing and are excluded; counting them would overstate the money '
                  'going in by more than the deposits themselves.',
            not_shown='How much of any balance’s rise is a deposit and how much is '
                      'interest. The two cannot be separated here.',
        ),
    ]
    # THE FUND THAT WAS SPENT, which is the whole answer to "can we use what is in
    # there" -- the town already has. Only visible because the ledger prints the balance
    # beside the creating article's amount; our own article extraction never saw the
    # withdrawal, because it sits inside an omnibus transfer about something else.
    hi_now = next((r['amount'] for r in rows if r['code'] == '8140'), None)
    hi_made = next((d['amount'] for d in dep
                    if 'health insurance' in d['subject'].lower()), None)
    if hi_now is not None and hi_made:
        rws.append(conclusion(
            id='a-stabilization-fund-has-already-been-spent-down',
            claim='The Health Insurance fund was created with %s and holds %s.'
                  % (C.usd(hi_made), C.usd(hi_now)),
            so_what='The town does spend these funds, and the articles that did it are '
                    'not in our record.',
            figures={'made': figure(hi_made, C.usd(hi_made), 'voted in at creation'),
                     'now': figure(hi_now, C.usd(hi_now), 'left in the fund'),
                     'gone': figure(hi_made - hi_now, C.usd(hi_made - hi_now),
                                    'gone, unexplained by any article we hold')},
            figure='gone', kind='measured', bearing='lever',
            detail='%s has left it, and not one article in this archive says so: the '
                   'withdrawals sit inside omnibus transfer articles about something '
                   'else. One of them is visible in the annual report as \u201ctransfer '
                   '$105,762.48 from the Health Insurance Stabilization Account\u201d, '
                   'inside an article that moves money from five different places at '
                   'once.' % C.usd(hi_made - hi_now),
            basis='The town\u2019s general ledger for the balance; `town_meeting_votes` '
                  'for the creating article.',
            not_shown='What the rest of the drawdown paid for, or which meeting approved '
                      'it. Only the ledger shows the money is gone.',
            allow=('$105,762.48',),
        ))
    if best and len(best) >= 3:
        rws.append(conclusion(
            id='the-deposits-ran-well-above-average-for-six-straight-years',
            claim='For %s straight years deposits ran between %s and %s.'
                  % (C.num(len(best)), C.usd(min(byfy[y] for y in best)),
                     C.usd(max(byfy[y] for y in best))),
            so_what='That run is what reducing the deposits would be worth against a '
                    'gap.',
            figures={'lo': figure(min(byfy[y] for y in best),
                                  C.usd(min(byfy[y] for y in best)), 'in the leanest year'),
                     'hi': figure(max(byfy[y] for y in best),
                                  C.usd(max(byfy[y] for y in best)), 'in the fullest year'),
                     'n': figure(len(best), C.num(len(best)), 'straight years'),
                     'a': figure(best[0], 'FY%d' % best[0]),
                     'b': figure(best[-1], 'FY%d' % best[-1])},
            figure='hi', kind='measured', bearing='sizes',
            detail='FY%d to FY%d: the consecutive years whose deposits exceeded the '
                   'long-run average, found by walking the series rather than by '
                   'choosing a window.' % (best[0], best[-1]),
            basis='`town_meeting_votes`, deposits summed per fiscal year.',
            not_shown='Whether the later fall is policy or a gap in what the warrant '
                      'printed — some recent articles carry no amount.',
        ))
    if fastest and slowest and fastest[0] != slowest[0]:
        rws.append(conclusion(
            id='the-funds-are-doing-three-different-things',
            claim='%s moved %s a year; %s moved %s.'
                  % (bare(fastest[0]), C.pct(_rate(fastest[1])), bare(slowest[0]),
                     C.pct(_rate(slowest[1]))),
            so_what='Two are being built; one is left alone to earn interest.',
            figures={'f': figure(_rate(fastest[1]), C.pct(_rate(fastest[1])),
                                 'a year, the fastest'),
                     's': figure(_rate(slowest[1]), C.pct(_rate(slowest[1])),
                                 'a year, the slowest')},
            figure='f', kind='measured', bearing='sizes',
            detail='Measured between each fund’s first and last PROVEN year, so the '
                   'spans differ and each is printed beside its bar. It is the movement '
                   'of a balance, not a rate of return.',
            basis='`stabilization_balances`, ending cash at each proven year.',
            not_shown='How much of either movement is money voted in rather than '
                      'interest earned.',
        ))

    data = dict(
        generated_by='scripts/build_stabilization.py',
        about='What the town holds in reserve, which of it could lawfully be spent on an '
              'operating deficit, how much goes in each year, and what the record cannot '
              'yet answer.',
        grain='DOLLARS. Balances are ending CASH at 30 June of each fiscal year, read off '
              'the town’s own trust-fund table and published only where the page’s '
              'own arithmetic closes. Deposits and withdrawals are what TOWN MEETING VOTED, '
              'which is not the same quantity and is not reconciled to the balances.',
        fy=FY,
        # THE STAT ROW, IN THE SAME SHAPE THE OTHER REPORTS USE. Each is a figure with its
        # UNIT attached, because a bare number in a stat box is the thing a reader is most
        # likely to quote and the thing this project's own rules say must never be
        # unitless -- dollars are not students and a count is not a rate.
        stats=[
            dict(value=usd0(gtot), tone='var(--series-cost)',
                 label='spendable on anything lawful, of %s held across %s funds'
                       % (usd0(total), len(rows))),
            dict(value=usd0(avg),
                 label='voted IN per year on average since FY%d — %s in total' % (lo, usd0(dep_total))),
            dict(value=usd0(spd_total),
                 label='voted back out, in the articles that say so plainly — a floor'),
        ],
        totals=dict(held=total, general=gtot, restricted=stot, funds=len(rows)),
        funds=[dict(code=r['code'], name=r['name'], balance=r['amount'],
                    general=r['code'] in GENERAL) for r in rows],
        flows=dict(
            deposits_total=dep_total, deposits_avg=avg, spends_total=spd_total,
            first_fy=lo, last_fy=hi, run=best,
            unpriced=len(fl['unpriced']), not_about=len(fl['not_about']),
            not_about_total=sum(x['amount'] for x in fl['not_about'] if x['amount']),
            by_year=[dict(fy=y, amount=byfy[y],
                          articles=sum(1 for d in dep if d['fy'] == y),
                          understated=y in short_years) for y in sorted(byfy)],
            by_fund=[dict(fund=f, total=sum(v.values()), years=len(v),
                          last_fy=max(v), last_amount=v[max(v)])
                     for f, v in funds_ranked],
            spends=[dict(fy=x['fy'], article=x['article'], subject=x['subject'],
                         amount=x['amount']) for x in sorted(spd, key=lambda r: r['fy'])],
        ),
        series=[dict(fund=f, rate=_rate(v), points=v) for f, v in
                sorted(series.items(), key=lambda kv: -kv[1][-1]['ending_cash'])],
        creations=[dict(fund=_fund_of(c['subject']), fy=int(c['fy']),
                        meeting=c['meeting'], article=c['article'],
                        result=c['result'], subject=c['subject'], quote=c['quote'])
                   for c in cre],
        missing_creations=missing,
        history={k: v for k, v in hist.items()},
        sources=_sources(),
        not_established=[
            'How much of any balance’s rise is money voted in and how much is interest.',
            'What the four funds with no creating article in this archive may lawfully be '
            'spent on — the limit currently rests on each fund’s NAME.',
            'Whether the fall in recent deposits is policy or a gap in what the warrant printed.',
            'The balances for six of the fifteen years; those pages have not yet yielded a '
            'row whose own arithmetic closes.',
        ],
        conclusions=emit('stabilization-funds', rws),
    )
    return data


def _rate(points):
    """Per cent a year between the first and last proven reading."""
    n = points[-1]['fy'] - points[0]['fy']
    a, b = points[0]['ending_cash'], points[-1]['ending_cash']
    return ((b / a) ** (1.0 / n) - 1) * 100 if n and a else 0.0


if __name__ == '__main__':
    sys.exit(main())
