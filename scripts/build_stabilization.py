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
import csv
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
usd0 = lambda x: '${:,.0f}'.format(x)

# WHICH FUND IS GENERAL AND WHICH IS RESTRICTED. This is the whole of question 5 and it is
# OURS, read off each fund's name rather than off a document that states the distinction --
# the annual report prints a balance and never says what may be spent on what. Marked as
# ours on the page for that reason. A special purpose stabilization fund is created for a
# stated purpose under c.40 s5B and may be spent only on it; the general fund may be
# appropriated for any lawful purpose.
GENERAL = {'8124'}


def gather():
    db = sqlite3.connect(DB); db.row_factory = sqlite3.Row
    rows = []
    for r in db.execute("SELECT label, v1, status FROM report_trust_funds WHERE fy=? "
                        "AND lower(label) LIKE '%stabil%'", (FY,)):
        m = re.search(r'\b(81\d\d)\b', r['label'] or '')
        name = ' '.join((r['label'] or '').split())
        if m:
            name = name.replace(m.group(1), '').strip()
        rows.append(dict(code=m.group(1) if m else '?', name=name,
                         amount=float(r['v1']), status=r['status']))
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


def render(rows):
    total = sum(r['amount'] for r in rows)
    gen = [r for r in rows if r['code'] in GENERAL]
    spec = [r for r in rows if r['code'] not in GENERAL]
    gtot = sum(r['amount'] for r in gen)
    stot = sum(r['amount'] for r in spec)
    b = []; w = b.append
    w('# The stabilization funds, and who may spend them\n')
    w('> **Working state:** `notes/HANDOFF.md` carries the current branch and what is\n'
      '> established versus assumed. `CLAUDE.md` carries the rules.\n')
    w('**What the town holds in reserve, which of it could lawfully be spent on an '
      'operating deficit, and the four questions about it this archive cannot yet '
      'answer.**\n')
    w('Analysis, September 2026. Balances are FY%d and are **not reconciled** — see '
      'the caveat before quoting one.\n' % FY)
    w('---\n')
    w('## The short version\n')
    w('The town holds **%s** across %d stabilization funds. **%s of it is the general '
      'Stabilization Fund, which Town Meeting may appropriate for any lawful purpose by a '
      'two-thirds vote. The remaining %s is restricted to the purpose each fund was '
      'created for.**\n'
      % (usd0(total), len(rows), usd0(gtot), usd0(stot)))
    w('So the answer to *can this pay for a school deficit* is **yes for %s and no for '
      'the rest** — and a reserve spent on an operating cost buys one year, exactly '
      'as free cash does, which is the argument `free-cash.md` already makes.\n'
      % usd0(gtot))
    w('---\n')
    w('## What is in them, FY%d\n' % FY)
    w('| account | fund | balance | may be spent on |\n|---|---|---:|---|')
    for r in rows:
        kind = ('**anything lawful**, by a 2/3 Town Meeting vote' if r['code'] in GENERAL
                else 'its own stated purpose only')
        w('| `%s` | %s | %s | %s |' % (r['code'], r['name'], usd(r['amount']), kind))
    w('| | **Total** | **%s** | |\n' % usd(total))
    w('**The general/restricted split is ours**, read off each fund’s name. The '
      'annual report prints a balance and never says what may be spent on what.\n')
    w('---\n')
    pv = proven()
    if pv:
        gen = [r for r in pv if r['name'].strip().upper().startswith('STABILIZATION')]
        w('## What has moved, so far as anything here can prove\n')
        w('These are the only stabilization figures in this archive that have been '
          '**checked**. Each is read off a photograph of the town\u2019s own trust-fund '
          'table and then verified against two identities the table states about every '
          'row \u2014 beginning plus activity equals ending cash, and ending cash plus '
          'unrealised equals ending market. A row that fails is not published.\n')
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
        w('Every proven row:\n')
        w('| year | account | fund | ending market |\n|---|---|---|---:|')
        for r in sorted(pv, key=lambda r: (r['fy'], r['name'])):
            w('| FY%s | `%s` | %s | %s |'
              % (r['fy'], r['code'] or '\u2014', ' '.join(r['name'].split())[:44],
                 usd(float(r['ending_market']))))
        w('')
        w('**Coverage is %d rows across %d years, and that is the point rather than a '
          'footnote.** The rest of the run is not missing because nobody looked \u2014 '
          'it is missing because those pages have not yet yielded a row whose arithmetic '
          'closes, and publishing one that does not would be worse than publishing '
          'nothing.\n' % (len(pv), len({r['fy'] for r in pv})))
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
    w('---\n')
    w('## Sources\n')
    w('| | |\n|---|---|')
    w('| Balances | `report_trust_funds`, from the annual town reports — status '
      '`no check` |')
    w('| The general/restricted split | ours, from each fund’s name |')
    w('| What the archive cannot yet say | `sources/data/money-gaps.csv`, side '
      '`extraction` |')
    return '\n'.join(b) + '\n'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out = render(gather())
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if out != cur:
            print('stabilization-funds.md is stale', file=sys.stderr); return 1
        print('stabilization-funds.md is current'); return 0
    open(OUT, 'w', encoding='utf-8').write(out)
    print('wrote %s' % os.path.relpath(OUT, ROOT)); return 0


if __name__ == '__main__':
    sys.exit(main())
