"""WHO THE SCHOOLS PAID, ONE YEAR AGAINST THE ONE BEFORE (fy-breakdown). TJ, 28 October 2026:
"a table that shows every vendor / payee paid for this FY, how much, and compared to just the
previous year (as a diff ...), call out new payees, call out dropped/unpaid payees from the year
before. and every payee becomes clickable to show what we bought from them, as well as the
school lines they are associated to ... im trying to see who we paid for services, how much,
changes in the year."

THE GRAIN: PAYMENTS. An invoice (`API`/`APM`) on a school expense account, in any fund the school
journal holds, in the year it was posted. Not orders still owed -- an order is not yet a payment
to anybody -- and not payroll, which carries no payee (journal.PAYROLL_GRAIN). So a year here is
what was paid in it, which for an order carried in from the year before is not the year it was
ordered (carried-over-orders says how much that moves).

THE GENERAL FUND'S SHARE (TJ, 28 October 2026: "the amount out of the general fund ... and the
percent that was covered by the general fund"): of what a payee was paid in the year, how much
came from fund 0100 -- the school budget and the district's other general fund accounts
(department 301, curriculum) -- and that as a share. Paid from fund 0100 and later re-charged
to a grant is still a general fund payment here: this is who paid the invoice, and the
re-charge is the line's story (the line table), not the payee's.

KEPT, AFTER RE-CHARGES -- OUR ALLOCATION (TJ, 28 October 2026: "some way to show the 'final
percent' out of the general fund, given transfers, moves, recharges"). A re-charge is posted
against a school LINE, never against an invoice, so the books do not say whose bill went. So
each school line's re-charged share -- what journal entries took off it, over what it spent
before them (fy_breakdown's `moved_off`) -- is applied to every general fund payment on that
line. Ours, an allocation, and labelled so on the page. Budget TRANSFERS move budget, not
payments, and do not enter. Cost moved BACK onto the general fund was paid by another fund
first and the books do not name whose bill it was, so it is a total in the summary, never a
payee's. A line re-charged more than it spent (one, a FY2024 salary line) is capped at all of
it, and refused if a payee was paid on it.

A PAYEE across years is journal.vendor_key() of the name the journal prints: the Town cuts names
at twenty characters and spells some two ways, and ALIASES joins the ones declared. A name the
redaction masked is one row, "Name withheld (redacted)", every year: it is many people, and it
is never compared to itself as if it were one.

NEW is paid this year and not the year before; NOT PAID THIS YEAR is the reverse. Both are about
THIS RUN: the journal starts in FY2023, so FY2023 has no year before and nothing is new in it.
Every payment ties: the school general fund to the period-13 report line by line, and every
special fund that report prints to the cent (fy_breakdown, verify_fy_breakdown), so a payee
absent from a year was not paid in it -- not merely unread.

Written as /data/fy-breakdown/payees-<year>.json, fetched when the block opens on a year.
"""
import json
import os
from collections import defaultdict
from decimal import Decimal

import journal as J

D0 = Decimal(0)
GF = '0100'


def whole(v):
    """A payee's year in whole dollars, as the rest of the page prints a total; each payment keeps
    its cents."""
    v = Decimal(v).quantize(Decimal(1))
    return ('-$%s' if v < 0 else '$%s') % format(abs(v), ',')
INVOICE = ('API', 'APM')
WITHHELD = 'Name withheld (redacted)'
NO_NAME = 'No payee printed'


def _key(r):
    p = J.payee(r)
    if isinstance(p, str):
        return p
    return WITHHELD if p is not None else NO_NAME


def payments():
    """(fy -> [(row, memo)]): every invoice on a school expense account, each under its fullest
    memo -- an invoice takes its order's memo through the release posted in the same entry."""
    A = J.accounts()
    by_fy = defaultdict(list)
    po, rel = {}, {}
    for r in J.lines():
        if r['source'] == 'POE':
            po[(r['fy'], r['doc_no'])] = r['description'].strip()
        elif r['source'] == 'POL':
            rel[(r['journal'], r['vendor'], -r['amt'])] = r['doc_no']
    for r in J.lines():
        if r['source'] not in INVOICE or r['posts_to'] != 'actual' or not J.is_expense(A[r['account']]):
            continue
        doc = rel.get((r['journal'], r['vendor'], r['amt']))
        memo = po.get((r['fy'], doc)) or r['description'].strip() or 'no memo'
        by_fy[r['fy']].append((r, memo))
    return by_fy


def files(m, line_name, fund_label, money, long_date, out_dir, fail):
    """The per-year files, and a summary per year for the block's own payload."""
    A = J.accounts()
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}

    def where(r):
        # a school budget line by its name; any other account by its own name and its fund
        if r['account'] in names:
            return names[r['account']], 'School budget'
        return r['account_description'].strip().title(), fund_label(r['fund'], A)

    pay = payments()
    years = sorted(pay)
    shown = defaultdict(lambda: defaultdict(int))   # key -> printed name -> count, every year
    tot = defaultdict(Decimal)                       # (fy, key)
    gf = defaultdict(Decimal)                        # (fy, key): paid from fund 0100
    kept = defaultdict(Decimal)                      # (fy, key): of that, kept after re-charges (ours)
    share, past = {}, set()
    for r in m['rows']:
        if not r['account']:
            continue
        before = r['gf_spent'] + r['moved_off'] - r['moved_on']
        if r['moved_off'] > before:
            past.add((r['fy'], r['account']))
        share[(r['fy'], r['account'])] = (D0 if not r['moved_off'] else Decimal(1) if r['moved_off'] >= before
                                          else r['moved_off'] / before)
    idx = defaultdict(list)                          # (fy, key) -> [(row, memo)]
    for fy in years:
        for r, memo in pay[fy]:
            k = _key(r)
            tot[(fy, k)] += r['amt']
            if r['fund'] == GF:
                gf[(fy, k)] += r['amt']
                f = share.get((fy, r['account']), D0)
                if (fy, r['account']) in past:
                    fail('FY%d %s: a payee paid on a line re-charged past what it spent' % (fy, r['account']))
                kept[(fy, k)] += r['amt'] * (1 - f)
            idx[(fy, k)].append((r, memo))
            shown[k][r['vendor'].strip() or k] += 1
    label = {k: max(c.items(), key=lambda kv: (kv[1], kv[0]))[0] if k not in (WITHHELD, NO_NAME) else k
             for k, c in shown.items()}

    def detail(fy, k):
        lines, bought, rows = defaultdict(Decimal), defaultdict(Decimal), []
        for r, memo in idx[(fy, k)]:
            ln, fund = where(r)
            lines[(ln, fund)] += r['amt']
            bought[(memo, ln)] += r['amt']
            rows.append([r['effective_date'], long_date(r['effective_date']), memo, ln, fund,
                         money(r['amt']), round(float(r['amt']), 2)])
        rows.sort(key=lambda x: (x[0], -abs(x[6])))
        srt = lambda d: sorted(d.items(), key=lambda kv: (-abs(kv[1]), kv[0]))
        return dict(l=[[a, b, whole(v), round(float(v), 2)] for (a, b), v in srt(lines) if round(v, 2)],
                    b=[[a, b, whole(v), round(float(v), 2)] for (a, b), v in srt(bought) if round(v, 2)],
                    r=rows)

    out, summary = {}, []
    for i, fy in enumerate(years):
        prev = years[i - 1] if i else None
        keys = {k for (y, k) in tot if y == fy or y == prev}
        rows = []
        for k in keys:
            v, pv = tot.get((fy, k), D0), tot.get((prev, k), D0) if prev else None
            paid, paid_before = (fy, k) in tot, prev is not None and (prev, k) in tot
            status = ('' if prev is None or k in (WITHHELD, NO_NAME) else
                      'new' if paid and not paid_before else 'dropped' if paid_before and not paid else '')
            d = detail(fy, k) if paid else detail(prev, k)
            g, kp = gf.get((fy, k), D0), kept.get((fy, k), D0)
            # a share only where the payee was paid something this year
            sh = (100 * g / v) if v > 0 else None
            ks = (100 * kp / v) if v > 0 else None
            rows.append(dict(k=k, n=label[k], v=round(float(v), 2), t=whole(v),
                             g=round(float(g), 2), gt=whole(g) if paid else None,
                             gs=None if sh is None else round(float(sh), 1),
                             gp=None if sh is None else '%d%%' % sh.quantize(Decimal(1)),
                             kt=whole(kp) if paid else None,
                             ks=None if ks is None else round(float(ks), 1),
                             kp=None if ks is None else '%d%%' % ks.quantize(Decimal(1)),
                             pv=None if pv is None else round(float(pv), 2),
                             pt=None if pv is None else whole(pv),
                             dv=None if pv is None else round(float(v - pv), 2),
                             dt=None if pv is None else ('+' if v > pv else '') + whole(v - pv),
                             s=status, c=len(idx[(fy, k)]),
                             of=None if paid else prev, **d))
        rows.sort(key=lambda x: (-abs(x['v']), -abs(x['pv'] or 0), x['n']))
        total = sum((tot[(fy, k)] for k in keys if (fy, k) in tot), D0)
        if sum((r['amt'] for r, _ in pay[fy]), D0) != total:
            fail('FY%d: the payees do not sum to the payments' % fy)
        body = dict(fy=fy, prev=prev, rows=rows, total=whole(total))
        out[os.path.join(out_dir, 'payees-%d.json' % fy)] = json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
        gf_total = sum((gf[(fy, k)] for k in keys if (fy, k) in gf), D0)
        kept_total = sum((kept[(fy, k)] for k in keys if (fy, k) in kept), D0)
        back = sum((r['moved_on'] for r in m['rows'] if r['fy'] == fy and r['account']), D0)
        summary.append(dict(gf=gf_total, gf_share=100 * gf_total / total if total else D0,
                            kept=kept_total, kept_share=100 * kept_total / total if total else D0, back=back,
            fy=fy, prev=prev, n=sum(1 for r in rows if r['c']),
            new=sum(1 for r in rows if r['s'] == 'new'), dropped=sum(1 for r in rows if r['s'] == 'dropped'),
            total=total, new_total=sum((Decimal(str(r['v'])) for r in rows if r['s'] == 'new'), D0),
            dropped_total=sum((Decimal(str(r['pv'])) for r in rows if r['s'] == 'dropped'), D0)))
    return out, summary
