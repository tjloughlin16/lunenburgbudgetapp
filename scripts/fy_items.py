"""ONE PAGE PER SCHOOL LINE AND PER FUND (fy-breakdown). TJ, 28 October 2026: *"i want people to be
able to share urls to direct links for each fund, school line.... so they should be able to share
a url to 'athletic fee fund', 'superintendent school line' etc. And whats on there should be what
shows up in the popup on the breakout pages"* -- and, per item, *"a chart ... similar to the canvas
chart at the bottom of the breakout page ... an isolated look"*, and *"history as line charts"*.

NOTHING HERE IS A NEW READING. Every file is a SLICE of what build_fy_breakdown.py already wrote in
the same run -- the page payload's line table and fund table rows, lines-<year>.json,
funds-<year>.json and web-<year>.json -- taken from the rendered texts, not recomputed, so the page
and the popup cannot disagree (rule 7d: one pass, one set of figures). The only figures made here
are a fund programme's per-year sums over its awards, for the history chart, formatted by the
same `money`.

IDENTITY, the way a reader names the thing:

    a SCHOOL LINE   a general fund account in the school budget, by its account number across
                    years; slug from its name as the line table prints it -- the line's own name
                    alone where no other line shares it, then name and heading, then the account.
    a FUND          a PROGRAMME across years (`journal.grant_program`): Title I is one page, each
                    year's award (fund 2705 in FY2024, 2839 in FY2026) listed on it. A fee or
                    revolving fund is its own programme; capital articles group by the name the
                    ledger gives them. Fund 0100 here is the general fund OUTSIDE the school
                    budget, which is how the fund table already names it.

Slugs are a pure function of the names over every year, so a rebuild gives the same addresses. A
new year can only change one if it brings a new line with a colliding name.

ASSERTED, per item and year, or nothing is written: a line's expense rows sum to what the school
budget spent and to what other funds paid; a fund award's postings sum to its total; every arrow
in an item's web is an arrow of that year's web; the slices equal the year files' entries.

    /data/fy-breakdown/index.json          every item: slug, kind, name, accounts or funds, years
    /data/fy-breakdown/line/<slug>.json    one school line, all years
    /data/fy-breakdown/fund/<slug>.json    one fund programme, all years
"""
import csv
import json
import os
import re
from collections import defaultdict
from decimal import Decimal
from statistics import median

import journal as J
import fy_breakdown as FB  # noqa: E402

D0 = Decimal(0)
SCHOOL = 'School budget'
# A PAYEE'S PUBLISHED PRICE (TJ, 28 October 2026: "we can show the rates directly on this page for
# comparison"). OURS, the pairing: FLLAC is now Keystone Educational Collaborative (fllac.org
# redirects there), and its invoices to Lunenburg are a quarter of the Key Program's member rate to
# the cent in FY2025-FY2027. The rates are read off the sheets (extract_keystone_tuition.py).
PAYEE_RATES = {'FLLAC EDUCATIONAL CO': dict(csv='keystone-tuition-rates.csv', program='Key Program', tier='Member',
                                            publisher='Keystone Educational Collaborative')}
# WHAT A BILL WAS FOR, from its memo (TJ, 28 October 2026: "analze the MEMOS now per payee... to see
# what memo 'category' has seen the most change"). OURS: a keyword list, first match wins, printed on
# the page beside what it sorted. MUNIS cuts a memo at about 18 characters and the clerk words the
# same bill differently year to year, so the raw words split one thing into many; keywords do not.
MEMO_CATS = [('extended', 'Extended year and summer', r'EXTEND|SUMMER|\bESY\b'),
             ('residential', 'Residential placement', r'\bRES\b|RESID'),
             ('day', 'Day placement', r'DAY\s*PLAC|DAY\s*PROG'),
             ('tuition', 'Tuition', r'TUIT|180\s*DAY'),
             ('transport', 'Transportation', r'TRANSP|\bBUS'),
             ('contract', 'Contracted services', r'CONTRACT|INTERFACE'),
             ('eval', 'Evaluation and testing', r'EVAL|ASSESS|TESTING')]
# The expense rows' kinds (build_fy_breakdown) folded into the four a reader needs to tell a year's
# own bills from another year's: everything not named here is a journal entry or a re-charge.
KIND_BUCKET = {'Invoice': 'invoice', 'Invoice, next year’s tuition paid early': 'early',
               'Order, still owed at year end': 'owed', 'Payroll': 'invoice', 'Receipt': 'invoice'}
# Lines read together (the group pages, /school-groups/<slug>): a district category whose lines
# share their payers. `what` is the page's one line.
# `counts`: which of the annual report's placement kinds each member line is read against, by the
# line's object code. OURS, and labelled so on the page: the report never ties a count to a line.
# What it rests on is the payees -- the collaborative line paid only collaboratives (FLLAC, CAPS)
# in FY2023-FY2026, and the private line only private schools and providers.
GROUPS = [dict(slug='out-of-district-tuition', cat='Out-of-district tuition', name='Out-of-district tuition',
               counts={'535023': ['collaborative'], '535019': ['day', 'residential']},
               what=('Every school line the district files as out-of-district tuition, read as one. Other funds '
                     'pay toward these lines too, and the money moves between them, so whether the cost is '
                     'steady can only be judged on all of them together.'))]
FUND_KINDS = ['payee', 'function', 'later', 'back', 'capital', 'between', 'none']


def slugify(s):
    s = s.lower().replace('’', '').replace("'", '')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def dec(text):
    """A formatted amount back to a Decimal: '$1,234.50' / '-$3.00'."""
    return Decimal(text.replace('$', '').replace(',', ''))


def cents(v):
    """A payload amount (a float rounded to the cent) as an exact Decimal."""
    return Decimal('%.2f' % v)


FLOWS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sources', 'data', 'school-fund-flows.csv')
FLOW_AMOUNTS = ('received_outside', 'received_not_in_journal', 'transfers_in', 'transfers_out', 'spent_actual',
                'spent_with_owed', 'net', 'opening_balance', 'closing_balance')


def fund_flows():
    """MONEY IN, MONEY OUT per fund per year: sources/data/school-fund-flows.csv, written and
    --check'ed by scripts/build_fund_flows.py. Amounts as Decimal; a balance nobody established
    is None, never zero."""
    out = []
    with open(FLOWS, newline='') as fh:
        for r in csv.DictReader(fh):
            for k in FLOW_AMOUNTS:
                r[k] = Decimal(r[k]) if r[k] != '' else None
            r['received'] = r['received_outside'] + r['received_not_in_journal']
            r['moved'] = r['transfers_in'] - r['transfers_out']
            if r['received'] + r['moved'] - r['spent_actual'] != r['net']:
                raise SystemExit('school-fund-flows.csv %s %s: received, moved and spent do not make its net'
                                 % (r['fiscal_year'], r['fund']))
            out.append(r)
    return out


def unique_slugs(items, tries):
    """items: {key: obj}; tries: functions obj -> candidate slug, from the shortest to the most
    specific; the last must be unique on its own. An item takes the first candidate that no other
    item has at the same try or at a LATER one -- a later try is that item's more specific name,
    and it outranks a shorter name of somebody else's ('IDEA preschool (pandemic relief)' does
    not take idea-preschool from 'IDEA (preschool)')."""
    cands = {k: [tr(o) for tr in tries] for k, o in items.items()}
    out = {}
    for k in sorted(items):
        for i, c in enumerate(cands[k]):
            clash = any(c in cands[o][i:] for o in items if o != k)
            if i == len(tries) - 1 or not clash:
                out[k] = c
                break
    if len(set(out.values())) != len(out):
        raise SystemExit('fy_items: two items share a slug')
    return out


def block(payload, comp):
    for b in payload['blocks']:
        if b.get('component') == comp:
            return b['data']
    raise SystemExit('fy_items: the page has no %s block' % comp)


def files(m, outs, page_path, out_dir, money, fail, plan=None):
    """-> {path: text}. `outs` is what build_fy_breakdown.main is about to write. `plan` is
    object code -> fy -> the approved book's printed gross and offset (build_fy_breakdown.
    printed_plan): where a book voted a line NET of money it counted on, the history says so."""
    page = json.loads(outs[page_path])
    L, F, W = block(page, 'fy-line-table'), block(page, 'fy-source-table'), block(page, 'fy-web')
    MV = block(page, 'fy-fund-moves')
    mv_y = {y['fy']: y['groups'] for y in MV['years']}
    years = [y['fy'] for y in L['years']]
    yfile = lambda kind, fy: json.loads(outs[os.path.join(out_dir, '%s-%s.json' % (kind, fy[2:]))])
    lines_y = {fy: yfile('lines', fy) for fy in years}
    funds_y = {fy: yfile('funds', fy) for fy in years}
    web_y = {fy: yfile('web', fy) for fy in years}

    # ---- identities
    line_rows = defaultdict(dict)              # account -> fy -> row
    for y in L['years']:
        for r in y['rows']:
            if r['line']:
                line_rows[r['account']][y['fy']] = r
    latest = lambda d: d[max(d)]
    line_slug = unique_slugs(
        {a: latest(d) for a, d in line_rows.items()},
        [lambda r: slugify(r['name'].split(' · ')[0]), lambda r: slugify(r['name']),
         lambda r: '%s-%s' % (slugify(r['name']), r['account'].split('-')[-1])])
    A = J.accounts()
    fund_acct = {}
    for a in A.values():
        fund_acct.setdefault(a['fund'], a)
    program = {}                               # fund -> programme name
    fund_rows = defaultdict(lambda: defaultdict(list))   # programme -> fy -> [row]
    flow_rows = fund_flows()
    for y in F['years']:
        for r in y['rows']:
            p = J.grant_program(fund_acct[r['key']])
            if p == 'General fund':
                p = r['program']               # 'General fund, outside the school budget'
            program[r['key']] = p
            fund_rows[p][y['fy']].append(r)
    fund_slug = unique_slugs(
        {p: p for p in fund_rows},
        [lambda p: slugify(re.sub(r'\s*\(.*?\)', '', p)), slugify,
         lambda p: '%s-%s' % (slugify(p), '-'.join(sorted({r['key'] for rs in fund_rows[p].values() for r in rs})))])
    node_href = {}
    for a, s in line_slug.items():
        node_href['l:' + a] = '/school-lines/' + s
    for f, p in program.items():
        node_href['f:' + f] = '/school-funds/' + fund_slug[p]
    LINE_PATH = '/school-lines/'
    # a payer as the expense rows name it (fy_breakdown.payer) -> its fund page, where that name
    # is ONE programme; a name covering several (revolving funds and lunch) links nowhere
    by_label = defaultdict(set)
    for f, p in program.items():
        by_label[FB.payer(fund_acct[f])].add(p)
    fund_path = {lb: '/school-funds/' + fund_slug[next(iter(ps))] for lb, ps in by_label.items() if len(ps) == 1}

    def ego(fy, centre):
        """The arrows of the year's web that touch the centre: what came in (left), what went out
        (right). Each node carries its own page's address where it has one."""
        w = web_y[fy]
        nodes = {n['id']: n for n in w['nodes']}
        es = [e for e in w['edges'] if e['a'] in centre or e['b'] in centre]
        ids = {e['a'] for e in es} | {e['b'] for e in es} | set(centre)
        ns = []
        for i in sorted(ids):
            if i not in nodes:
                fail('%s: the web has no node %s' % (fy, i))
            n = dict(nodes[i])
            if i in node_href:
                n['href'] = node_href[i]
            ns.append(n)
        return dict(centre=sorted(centre), nodes=ns, edges=es)

    out = {}
    index = dict(lines=[], funds=[])

    # ---- WHERE A LINE'S PAYERS WENT (TJ, 28 October 2026: "if those funds dry up, or come in fresh,
    # they go somewhere else or come from somewhere else ... 'previously paid by circuit breaker in
    # FY25, but then in FY26 circuit breaker went to XYZ'"). Every other fund's spending on every
    # school line, each year, from the same expense rows the line pages tie to.
    fund_on = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))   # fy -> fund -> account -> amount
    for fy in years:
        lf = lines_y[fy]
        for a_, by_ in line_rows.items():
            r_ = by_.get(fy)
            ex_ = lf['lines'].get(r_['key']) if r_ else None
            for x in (ex_['r'] if ex_ else []):
                f_ = lf['funds'][x[6]]
                if f_ != SCHOOL:
                    fund_on[fy][f_][a_] += dec(x[7])

    def trace(a):
        return trace_of({a})

    TRACE_LINES = 3    # OURS: how many of a payer's other lines get a colour of their own
    def trace_of(here_set):
        """For each fund that paid toward line `a` in any year: every year, what it put here, what
        it put on other school lines (the largest three, then the rest), and one sentence where it
        arrived or left."""
        name = lambda acc: latest(line_rows[acc])['name'].split(' · ')[0]
        out_ = []
        for f in sorted({f for fy in years for f in fund_on[fy] if any(fund_on[fy][f].get(x) for x in here_set)}):
            ys_ = []
            for fy in years:
                on = fund_on[fy].get(f, {})
                here = sum((on.get(x, D0) for x in here_set), D0)
                rest = sorted(((v, acc) for acc, v in on.items() if acc not in here_set and v), reverse=True)
                total = sum(on.values(), D0)
                # a group's members, each: which of them the fund paid, so a shift between them shows
                split = [dict(name=name(x), v=float(on.get(x, D0)), t=money(on.get(x, D0)))
                         for x in sorted(here_set)] if len(here_set) > 1 else []
                ys_.append(dict(fy=fy, here=float(here), total=float(total), split=split,
                                t=dict(here=money(here), total=money(total), elsewhere=money(total - here),
                                       rest=money(sum((v for v, _ in rest[3:]), D0)) if rest[3:] else ''),
                                top=[dict(name=name(acc), href=LINE_PATH + line_slug[acc], v=float(v), t=money(v))
                                     for v, acc in rest[:3]]))
            notes = []
            for prev, cur in zip(ys_, ys_[1:]):
                if prev['here'] and not cur['here']:
                    notes.append('Paid %s here in %s, nothing in %s%s' % (
                        prev['t']['here'], prev['fy'], cur['fy'],
                        ('; its largest school line that year was %s, %s' % (cur['top'][0]['name'], cur['top'][0]['t'])
                         if cur['top'] else '; it paid no school line that year')))
                elif cur['here'] and not prev['here']:
                    notes.append('New here in %s, %s%s' % (
                        cur['fy'], cur['t']['here'],
                        ('; in %s its largest school line was %s, %s' % (prev['fy'], prev['top'][0]['name'], prev['top'][0]['t'])
                         if prev['top'] else '; in %s it paid no school line' % prev['fy'])))
            # THE SAME OTHER LINES EVERY YEAR (TJ, 29 October 2026: the per-year bars were unreadable).
            # The fund's largest other school lines across all the years, a fixed set, so each keeps
            # its colour and its place in the stack year to year; the rest is one segment.
            span_ = defaultdict(Decimal)
            for fy in years:
                for acc, v in fund_on[fy].get(f, {}).items():
                    if acc not in here_set and v:
                        span_[acc] += v
            fixed = [acc for acc, _ in sorted(span_.items(), key=lambda kv: (-kv[1], kv[0]))[:TRACE_LINES]]
            for fy, y in zip(years, ys_):
                on = fund_on[fy].get(f, {})
                here = sum((on.get(x, D0) for x in here_set), D0)
                by_ = [on.get(acc, D0) for acc in fixed]
                others = sum(on.values(), D0) - here - sum(by_, D0)
                if here + sum(by_, D0) + others != sum(on.values(), D0):
                    fail('%s %s %s: the stack does not add to what it spent on school lines' % (fy, f, sorted(here_set)))
                y['by'] = [dict(v=float(v), t=money(v) if v else '') for v in by_]
                y['others'] = float(others)
                y['t']['others'] = money(others) if others else ''
            out_.append(dict(fund=f, href=fund_path.get(f), years=ys_, notes=notes,
                             lines=[dict(name=name(acc), href=LINE_PATH + line_slug[acc]) for acc in fixed]))
        return out_

    # ---- school lines
    line_hist = {}
    line_rates = {}
    for a, by in sorted(line_rows.items()):
        slug = line_slug[a]
        ys = {}
        hist = []
        payees_y, kinds_y = {}, {}
        memo_y = defaultdict(lambda: defaultdict(Decimal))     # (payee, category) -> fy -> amount
        memo_rows = defaultdict(lambda: defaultdict(Decimal))  # payee -> fy -> this year's tuition invoices
        other_memos = defaultdict(Decimal)
        for fy in years:
            r = by.get(fy)
            if not r:
                continue
            lf = lines_y[fy]
            ex = lf['lines'].get(r['key'])
            # THE ROWS TIE: the school budget's rows to what it spent, the rest to what other
            # funds paid toward the line (the table's two cost columns)
            sch = [i for i, f in enumerate(lf['funds']) if f == SCHOOL]
            mine = sum((dec(x[7]) for x in (ex['r'] if ex else []) if x[6] in sch), D0)
            other = sum((dec(x[7]) for x in (ex['r'] if ex else []) if x[6] not in sch), D0)
            if mine != cents(r['n']['spent']):
                fail('%s %s: its rows sum to %s, the school budget spent %s' % (fy, a, mine, r['n']['spent']))
            if other != cents(r['n']['total']) - cents(r['n']['spent']):
                fail('%s %s: other funds’ rows sum to %s, the table says %s' % (
                    fy, a, other, cents(r['n']['total']) - cents(r['n']['spent'])))
            # WHO IT PAID AND WHAT KIND OF BILL (TJ, 28 October 2026: "breakdowns and charts per
            # payee maybe to see what increased over time"). Every row of the line, all funds. Bills
            # are counted and their median taken per payee, so a reader can tell MORE bills from
            # BIGGER bills -- a count of invoices, never a count of children.
            rows_ = ex['r'] if ex else []
            pay = defaultdict(lambda: [D0, []])
            kind = defaultdict(Decimal)
            for x in rows_:
                k = lf['kinds'][x[2]]
                v = dec(x[7])
                kind[KIND_BUCKET.get(k, 'other')] += v
                if x[3] and k in ('Invoice', 'Invoice, next year’s tuition paid early', 'Order, still owed at year end'):
                    pay[x[3]][0] += v
                    if k == 'Invoice' and v > 0:
                        pay[x[3]][1].append(v)
            for x in rows_:
                k = lf['kinds'][x[2]]
                if not x[3] or k not in ('Invoice', 'Invoice, next year’s tuition paid early', 'Order, still owed at year end'):
                    continue
                c = next((c for c, _, rx in MEMO_CATS if re.search(rx, x[4].upper())), 'other')
                memo_y[(x[3], c)][fy] += dec(x[7])
                if c == 'tuition' and k == 'Invoice':
                    memo_rows[x[3]][fy] += dec(x[7])
                if c == 'other':
                    other_memos[x[4].strip()] += dec(x[7])
            payees_y[fy] = {pn: dict(v=float(tv), t=money(tv), n=len(inv),
                                     med=float(median(inv)) if inv else None, t_med=money(median(inv)) if inv else '')
                            for pn, (tv, inv) in pay.items() if tv}
            kinds_y[fy] = {k: dict(v=float(v), t=money(v)) for k, v in kind.items() if v}
            web = ego(fy, ['l:' + a])
            ys[fy] = dict(row=r, funds=lf['funds'], kinds=lf['kinds'], ex=ex, mv=lf['mv'].get(r['key']), web=web)
            # WHO ELSE PAID, FUND BY FUND (TJ, 28 October 2026: "show how much was paid year by year
            # from the other funds ... that way we can show if its flat all-in, or changing"). The
            # rows above, summed per fund; they tie to `other` because the rows do.
            by_fund = defaultdict(Decimal)
            for x in (ex['r'] if ex else []):
                if x[6] not in sch:
                    by_fund[lf['funds'][x[6]]] += dec(x[7])
            h = dict(fy=fy, voted=r['n']['voted'], budget=r['n']['budget'], spent=r['n']['spent'],
                     other=round(r['n']['total'] - r['n']['spent'], 2), all_in=r['n']['total'],
                     paid=[dict(fund=f, v=float(v), t=money(v)) for f, v in sorted(by_fund.items()) if v],
                     left=r['n']['left'],
                     t=dict(voted=r['t']['voted'], budget=r['t']['budget'], spent=r['t']['spent'],
                            other=money(cents(r['n']['total']) - cents(r['n']['spent'])),
                            all_in=money(cents(r['n']['total'])), left=money(cents(r['n']['left']))))
            # A VOTE NET OF WHAT THE BOOK COUNTED ON (TJ, 28 October 2026, of collaborative
            # tuitions: "why would it have a 0 budget for a year!"). FY2025's vote was the book's
            # gross less the circuit breaker it expected; FY2023's was gross. Drawn as one series
            # that reads as the line collapsing, so the year carries the book's gross beside it.
            p = (plan or {}).get(a.rsplit('-', 1)[1], {}).get(int(fy[2:]))
            if p and p['offset'] is not None:
                if cents(p['gross']) - cents(p['offset']) != cents(r['n']['voted']):
                    fail('%s %s: the book’s %s less %s is not the %s voted' % (fy, a, p['gross'], p['offset'], r['n']['voted']))
                h['gross'] = float(cents(p['gross']))
                h['t'].update(gross=money(cents(p['gross'])), net=(
                    'Voted net: the approved budget plans %s and counts %s from the state circuit breaker'
                    % (money(cents(p['gross'])), money(cents(p['offset'])))))
            hist.append(h)
        line_hist[a] = hist
        rates = payee_rates(payees_y, memo_rows, money)
        line_rates[a] = rates
        lr = latest(by)
        out[os.path.join(out_dir, 'line', slug + '.json')] = dump(dict(rates=rates,
            slug=slug, name=lr['name'], account=a, cat=lr['cat'], years=ys, history=hist, payers=trace(a),
            payees=payees_out(payees_y, money), bill_kinds=kinds_y, memos=memos_out(memo_y, other_memos, years, money)))
        index['lines'].append(dict(slug=slug, name=lr['name'], account=a, cat=lr['cat'], years=sorted(ys)))

    # which programme a fund in a move belongs to: as the table names it, else by its name (an
    # award that spent nothing this year can still have had cost moved off it)
    # ---- GROUPS OF LINES (TJ, 28 October 2026: "A specific sort of combined fund page? lets do
    # that"). Lines whose money moves between them -- the circuit breaker and IDEA are charged to
    # either tuition line, and placements may be booked to either -- so the question "is it flat
    # all-in" has to be asked of the group. Members are the district's own category, read off the
    # rows, never a list of account numbers typed here.
    index['groups'] = []
    for g in GROUPS:
        members = sorted(a for a, by in line_rows.items() if latest(by)['cat'] == g['cat'])
        if len(members) < 2:
            fail('group %s: %d lines in category %r, not two or more' % (g['slug'], len(members), g['cat']))
        hist = []
        for fy in years:
            hs = [h for a in members for h in line_hist[a] if h['fy'] == fy]
            if not hs:
                continue
            tot = lambda k: sum((cents(h[k]) for h in hs), D0)
            paid = defaultdict(Decimal)
            for h in hs:
                for p_ in h['paid']:
                    paid[p_['fund']] += cents(p_['v'])
            h = dict(fy=fy, **{k: float(tot(k)) for k in ('voted', 'budget', 'spent', 'other', 'all_in', 'left')},
                     paid=[dict(fund=f, v=float(v), t=money(v)) for f, v in sorted(paid.items()) if v],
                     t={k: money(tot(k)) for k in ('voted', 'budget', 'spent', 'other', 'all_in', 'left')})
            if any('gross' in x for x in hs):
                # a member voted net adds its book's gross; a member voted gross adds its vote
                gross = sum((cents(x['gross']) if 'gross' in x else cents(x['voted']) for x in hs), D0)
                h['gross'] = float(gross)
                h['t'].update(gross=money(gross), net='; '.join(
                    '%s: %s' % (latest(line_rows[a])['name'].split(' · ')[0], x['t']['net'][0].lower() + x['t']['net'][1:])
                    for a in members for x in line_hist[a] if x['fy'] == fy and 'net' in x['t']))
            hist.append(h)
        # each member, each year: the table under the charts
        table = []
        for fy in years:
            for a in members:
                x = next((x for x in line_hist[a] if x['fy'] == fy), None)
                if x:
                    left = cents(x['budget']) - cents(x['spent'])
                    table.append(dict(fy=fy, name=latest(line_rows[a])['name'].split(' · ')[0], href=LINE_PATH + line_slug[a],
                                      t=dict(voted=x['t']['voted'], budget=x['t']['budget'], spent=x['t']['spent'],
                                             other=x['t']['other'], all_in=x['t']['all_in'], left=money(left)),
                                      n=dict(left=float(left))))
        payers = trace_of(set(members))
        # OTHER MOVES THAT SHIFTED MONEY (TJ, 28 October 2026: "or other chnages that happened to
        # shift money around"): budget moved between lines, orders carried in, bills re-charged
        # between the school budget and other funds, bills other funds paid from the start. The
        # line table's own columns and words (frame.line.columns), each line each year, where any moved.
        SHIFT = ('transfers', 'carried', 'off', 'on', 'direct')
        shifts = []
        for fy in years:
            for a in members:
                r_ = line_rows[a].get(fy)
                if r_ and any(r_['n'].get(k) for k in SHIFT):
                    shifts.append(dict(fy=fy, name=latest(line_rows[a])['name'].split(' · ')[0], href=LINE_PATH + line_slug[a],
                                       n={k: r_['n'].get(k, 0.0) for k in SHIFT},
                                       t={k: money(cents(r_['n'].get(k, 0.0))) if r_['n'].get(k) else '' for k in SHIFT}))
        counts = placement_counts([int(fy[2:]) for fy in years], fail) if g.get('counts') else None
        for a in members:
            if g.get('counts') and a.rsplit('-', 1)[1] not in g['counts']:
                fail('group %s: line %s has no placement kinds to be read against' % (g['slug'], a))
        out[os.path.join(out_dir, 'group', g['slug'] + '.json')] = dump(dict(counts=counts,
            slug=g['slug'], name=g['name'], what=g['what'], cat=g['cat'],
            members=[dict(name=latest(line_rows[a])['name'].split(' · ')[0], account=a, href=LINE_PATH + line_slug[a],
                          history=line_hist[a], rates=line_rates[a], counts=(g.get('counts') or {}).get(a.rsplit('-', 1)[1], []))
                     for a in members],
            history=hist, table=table, payers=payers, shifts=shifts))
        # the fund pages that paid toward the group link back to it (TJ, 28 October 2026: "make
        # sure the individual funds reference the combined page too")
        index['groups'].append(dict(slug=g['slug'], name=g['name'], members=members,
                                    funds=sorted(p_['href'][len('/school-funds/'):] for p_ in payers if p_['href'])))

    def prog_of(f):
        if f in program:
            return program[f]
        return J.grant_program(fund_acct[f]) if f != '0100' else 'General fund, outside the school budget'

    # ---- fund programmes
    for p, by in sorted(fund_rows.items()):
        slug = fund_slug[p]
        ys = {}
        hist = []
        for fy in years:
            rows = sorted(by.get(fy, []), key=lambda r: -abs(r['n']['total']))
            if not rows:
                continue
            awards = []
            sums = defaultdict(Decimal)
            for r in rows:
                body = funds_y[fy]['funds'].get(r['key'])
                if body is None:
                    fail('%s fund %s: in the table, not in funds-%s.json' % (fy, r['key'], fy[2:]))
                posted = sum((dec(x[7]) for x in body['r']), D0)
                if posted != cents(r['n']['total']):
                    fail('%s fund %s: its postings sum to %s, the table says it spent %s' % (fy, r['key'], posted, r['t']['total']))
                where = sum((dec(x[2]) for x in body['w']), D0)
                if where != cents(r['n']['total']):
                    fail('%s fund %s: where it went sums to %s, not %s' % (fy, r['key'], where, r['t']['total']))
                for k in FUND_KINDS + ['total']:
                    sums[k] += cents(r['n'][k])
                awards.append(dict(row=r, body=body))
            if sum((sums[k] for k in FUND_KINDS), D0) != sums['total']:
                fail('%s %s: the kinds do not sum to the total' % (fy, p))
            web = ego(fy, ['f:' + r['key'] for r in rows])
            # COST MOVED BETWEEN FUNDS that touched one of its awards, as the page's block groups
            # it: between two of its own awards (the `award` class), or with another fund
            moves = [g for g in mv_y.get(fy, []) if any(prog_of(f) == p for f in g['funds'])]
            ys[fy] = dict(awards=awards, web=web, moves=moves)
            hist.append(dict(fy=fy, n={k: round(float(v), 2) for k, v in sums.items()},
                             t={k: money(v) for k, v in sums.items()},
                             awards=[dict(fund=r['key'], name=r['name'], t=r['t']['total']) for r in rows],
                             moves=[g for g in moves if g['cls'] == 'award']))
        first = by[max(by)][0]
        # MONEY IN, MONEY OUT, ACROSS THE YEARS (TJ, 29 October 2026: "revenue and expense charts
        # per fund, to show if the accounts are being consistently drained and filled"): its awards
        # added; a balance only where every award has one
        flows = []
        for fy_n in sorted({int(r['fiscal_year']) for r in flow_rows if r['program'] == p}):
            xs = [r for r in flow_rows if r['program'] == p and int(r['fiscal_year']) == fy_n]
            n = {k: sum((x[k] for x in xs), D0) for k in ('received', 'moved', 'spent_actual', 'net')}
            bal = sum((x['closing_balance'] for x in xs), D0) if all(x['closing_balance'] is not None for x in xs) else None
            flows.append(dict(fy='FY%d' % fy_n, open=any(x['year_open'] == 'yes' for x in xs),
                              n=dict(received=float(n['received']), moved=float(n['moved']), spent=float(n['spent_actual']),
                                     net=float(n['net']), balance=None if bal is None else float(bal)),
                              t=dict(received=money(n['received']), moved=money(n['moved']) if n['moved'] else '',
                                     spent=money(n['spent_actual']), net=money(n['net']),
                                     balance='' if bal is None else money(bal))))
        out[os.path.join(out_dir, 'fund', slug + '.json')] = dump(dict(
            slug=slug, name=p, cat=first['cat'], group=first['group'], years=ys, history=hist, flows=flows))
        index['funds'].append(dict(slug=slug, name=p, cat=first['cat'], group=first['group'],
                                   funds=sorted({r['key'] for rs in by.values() for r in rs}),
                                   years=sorted(ys)))

    # every arrow an item draws is one of its year's web, and the item files hold every arrow of
    # every web that touches a line or fund with a page
    for path, text in out.items():
        d = json.loads(text)
        for fy, y in d.get('years', {}).items():      # a group page draws no web of its own
            have = {json.dumps(e, sort_keys=True) for e in web_y[fy]['edges']}
            for e in y['web']['edges']:
                if json.dumps(e, sort_keys=True) not in have:
                    fail('%s %s: an arrow not in the year’s web' % (os.path.basename(path), fy))

    # THE FRAME: the column definitions and every string the popups use, from the page's own
    # blocks, so the item pages say what the popups say
    strip = lambda d: {k: v for k, v in d.items() if k != 'years'}
    span = '%s–%s' % (years[0], years[-1])
    index.update(
        years=years, span=span, sources=page['sources'],
        frame=dict(line=strip(L), fund=strip(F), web=strip(W), moves=strip(MV)),
        text=dict(
            k_line='School line', k_fund='Fund', parent='FY breakdown', parent_href='/school-all-funds/fy-breakdown',
            line_what=('One line of the school budget: what Town Meeting voted for it, what it spent, '
                       'and what other funds paid toward it.'),
            fund_what=('A fund other than the school budget that spent money on the schools: where '
                       'its money went, what it bought, every posting.'),
            web_h='What it connects to', web_line=('Left: the funds that paid toward this line, and lines '
                                                   'that gave it budget. Right: funds bills were moved back to, '
                                                   'and lines it gave budget to.'),
            web_fund=('Centre: this fund (each award, where a programme has several). Right: where its '
                      'money went. Left: bills moved back onto it from a school line.'),
            web_none='Nothing connects to it this year but what is shown.',
            web_inner='Between its own awards', web_took='re-booked cost to',
            mv_h='Cost moved between funds',
            mv_awards_h='Its awards, and cost moved between them',
            mv_awards=('Each year’s awards side by side, with what they spent, and every entry that '
                       're-booked cost from one of its awards to another.'),
            mv_none_awards='No entry moved cost between its awards in these years.',
            web_from='In', web_to='Out', web_open='Open its page',
            web_view='Show as', web_view_chart='Chart', web_view_table='Table',
            web_th_other='The other end', web_none_row='None this year.', web_th_kind='Kind of connection', web_th_amount='Amount',
            web_ours='Paid from the start and same kind of work are our matches; re-charges and '
                     'moves are the Town’s own entries.',
            hist_h='Across the years', hist_span='The years the journal covers',
            hist_budget='Budget', hist_spend='Spending', voted='Voted', budget='Final budget',
            hist_both='Budget against spending', gross='Planned before the circuit breaker',
            spent='Spent by the school budget', other='Paid by other funds',
            all_in='Everything it cost, all funds',
            left_row='Left in the budget',
            left_note=('Left is the budget less what the school budget itself spent. Money another fund paid '
                       'counts toward the cost but not against the budget, so Left can be larger than the gap '
                       'between the budget line and the top of the bar.'),
            fl_h='Money in, money out',
            fl_line=('What the fund received each year beside what it spent, and what it held at 30 June. '
                     'Where the bars are level the fund spent what it took in; where spending stands taller '
                     'it drew on its balance.'),
            fl_received='Received', fl_moved='Moved between funds', fl_spent='Spent',
            fl_net='Received less spent', fl_balance='Held at 30 June', fl_unknown='not known',
            fl_open='Still open in the journal: received and spent to date.',
            fl_no_balance=('No opening balance was found for this fund, so what it held is not known; the '
                           'received and spent figures stand on their own.'),
            payers_h='Where its other payers went',
            payers_line=('Each fund other than the school budget that paid toward this line in any year: '
                         'what it put here, and what it put on other school lines the same year. Each bar is '
                         'everything the fund spent on school lines that year; the bottom of it, in colour, is this '
                         'line.'),
            payers_group=('Each fund other than the school budget that paid toward any of these lines: what it '
                          'put on them, and what it put on other school lines the same year. Each bar is '
                          'everything the fund spent on school lines that year; the bottom of it, in colour, is '
                          'these lines.'),
            trace_here='This line', trace_here_group='These lines', trace_rest='Every other school line',
            trace_lines='Its largest other school lines, all years:',
            k_group='Lines read together', with_group='Read with the others:', paid_group='It paid toward',
            split_h='Which line each fund paid',
            split_line=('One chart per fund other than the school budget: each year’s bar is everything it '
                        'spent on school lines, split by which of these lines it paid, and the rest.'),
            split_rest='Its other school lines',
            payees_h='Who it paid, by year',
            payees_line='Every fund. The payees it paid most across the years, by name; the rest together.',
            payees_rest='Everyone else',
            kinds_h='What kind of bill, by year',
            kinds_line=('This year’s bills, next year’s paid early, and orders still owed at year end, kept apart: a '
                        'jump can be a year paying for two.'),
            k_invoice='This year’s bills', k_early='Next year’s tuition, paid early', k_owed='Owed at year end',
            k_other='Journal entries and re-charges',
            bills_h='How many bills, and how big',
            bills_line=('For each payee: how many invoices it sent, and the middle invoice’s amount. More invoices '
                        'and bigger invoices are different causes. A count of invoices is not a count of children: '
                        'one invoice can cover a part of a year, or more than one child.'),
            n_bills='invoices', med_bill='median invoice',
            memos_h='What the bills were for',
            memos_line=('Each bill sorted by words in its memo. The grouping is ours: a keyword list, shown below, '
                        'first match wins. The town’s system cuts a memo at about 18 characters and the wording '
                        'changes year to year, so the words themselves cannot be compared; the groups can.'),
            memos_change='Largest changes, by payee and kind of bill', c_other='Other memos',
            memos_words='Keywords', memos_unsorted='Memos no keyword matched', change_col='Change',
            rates_h='The published price',
            rates_line=('What the collaborative’s own rate sheet prints each year, beside what this line was billed. '
                        'Pairing the payee with the sheet is ours; it rests on the invoices matching the printed rate.'),
            r_sy='School year', r_day='Day rate', r_ext='Extended year', r_45='Initial 45 days, per day',
            r_med='Median invoice here', r_billed='This year’s tuition bills', r_years='At the annual rate',
            r_years_note=('This year’s tuition bills divided by the annual rate: how many years of tuition the bills '
                          'add up to, roughly. Not children: two half-years make one, and some bills are for other '
                          'programmes at other prices.'),
            r_years_unit='years of tuition', r_sheet='rate sheet',
            counts_h='Children placed out of district',
            counts_line=('Children in out-of-district placements on 1 March, as the annual town report prints '
                         'them, by kind of placement. A count of children, not of dollars: no cost per child '
                         'is drawn from it.'),
            counts_unit='children', c_collab='Collaborative program', c_day='Private day school',
            c_res='Private residential school', c_total='All placements',
            counts_def=('A day placement: the child attends that school and comes home each night. Residential: '
                        'the child lives at the school. Both are private schools; a collaborative is a public '
                        'programme run jointly by several districts.'),
            compare_h='Each line, side by side',
            compare_line=('The same years and the same scale across each row, so the two lines compare directly: '
                          'the children placed, the budget, and what it cost by who paid.'),
            r_counts='Children placed, 1 March', r_budget='Budget', r_spend='What it cost, by who paid',
            both_h='Both lines added together',
            counts_ours=('Reading collaborative placements against the collaborative tuition line, and day and '
                         'residential against private tuitions, is ours: the report does not tie its counts to '
                         'budget lines. It rests on who was paid -- the collaborative line paid only '
                         'collaboratives, the private line only private schools and providers.'),
            counts_missing='not printed in the reports held',
            counts_unheld='no annual town report for this year is in the archive yet',
            counts_src='Annual town report', counts_page='p.',
            shifts_h='Other moves that shifted money',
            shifts_line=('Each line, each year, wherever budget or bills moved. Hover a heading for what it means.'), members='The lines', each_h='Each line, each year',
            left='Left on the line',
            here='Here', elsewhere='Its other school lines', rest='everything else', on_lines='on school lines',
            hist_rule='A budget is what was allowed and spending is what happened: they are drawn '
                      'side by side, never added into one series.',
            hist_where='Where it went, by year', hist_total='Everything it spent',
            awards='Awards this year', award='Award', not_this_year='Not on the books this year.',
            year='Year', sources='Sources', link='Open its page',
            in_year='in', not_found='No such line or fund.',
            loading='Loading…', failed='Could not load this page’s data.',
            sources_note='Every figure is from the school journal and ties to the Town’s period-13 report.'))
    out[os.path.join(out_dir, 'index.json')] = dump(index)
    return out


PAYEE_TOP = 5


def payee_rates(payees_y, tuition, money):
    """For a payee with a published rate sheet: each year's printed rates beside the median invoice
    the line received from it, and its own-year tuition bills divided by the annual rate -- a
    conversion of dollars at a published price, approximate where some bills are for other
    programmes at other prices, and never a count of children."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_ = []
    for payee, cfg in PAYEE_RATES.items():
        if not any(payee in ps for ps in payees_y.values()):
            continue
        rows = [r for r in csv.DictReader(open(os.path.join(root, 'sources', 'data', cfg['csv']), encoding='utf-8'))
                if r['program'] == cfg['program'] and r['tier'] == cfg['tier']]
        by = defaultdict(dict)
        for r in sorted(rows, key=lambda r: r['document']):      # the later upload of a year wins
            by[int(r['fy'])][r['rate_type']] = r
        years_ = []
        for f in sorted(by):
            fy = 'FY%d' % f
            sy = by[f].get('school_year')
            x = payees_y.get(fy, {}).get(payee)
            billed = tuition.get(payee, {}).get(fy, D0)
            years_.append(dict(
                fy=fy, href='/docs/' + sy['document'] if sy else None, page=int(sy['page']) if sy else None,
                t={k: by[f][k]['amount_as_printed'] for k in ('school_year', 'day', 'extended_year', 'initial_45_day') if k in by[f]},
                ext_label=by[f]['extended_year']['column_heading_as_printed'] if 'extended_year' in by[f] else '',
                t_med=x['t_med'] if x else '', t_billed=money(billed) if billed else '',
                years=round(float(billed / Decimal(sy['amount'])), 1) if billed and sy else None))
        out_.append(dict(payee=payee, publisher=cfg['publisher'], program=cfg['program'], tier=cfg['tier'],
                         csv='/docs/data/' + cfg['csv'], years=years_))
    return out_


def memos_out(memo_y, other_memos, years, money):
    """Each (payee, category) across the years, and its change from the year before the last to the
    last, largest change first -- the question asked of it. Shown only where the keywords sorted at
    least half of the money; elsewhere `shown` is false and the page leaves the section out."""
    tot = sum((abs(v) for by in memo_y.values() for v in by.values()), D0)
    sorted_ = sum((abs(v) for (p, c), by in memo_y.items() if c != 'other' for v in by.values()), D0)
    last, prev = years[-1], years[-2] if len(years) > 1 else None
    rows = []
    for (p, c), by in memo_y.items():
        ch = by.get(last, D0) - (by.get(prev, D0) if prev else D0)
        rows.append(dict(payee=p, cat=c, n={fy: float(by.get(fy, D0)) for fy in years},
                         t={fy: money(by[fy]) if by.get(fy) else '' for fy in years},
                         change=float(ch), t_change=('+' if ch > 0 else '') + money(ch) if ch else ''))
    rows.sort(key=lambda r: (-abs(r['change']), r['payee'], r['cat']))
    by_cat = {}
    for fy in years:
        by_cat[fy] = {c: dict(v=float(v), t=money(v)) for c in [c for c, _, _ in MEMO_CATS] + ['other']
                      for v in [sum((by.get(fy, D0) for (p, c2), by in memo_y.items() if c2 == c), D0)] if v}
    return dict(shown=bool(tot) and sorted_ * 2 >= tot, rows=rows[:12], by_cat=by_cat, last=last, prev=prev,
                cats=[dict(id=c, label=l, words=rx.replace('\\b', '').replace('\\s*', ' ').replace('|', ', '))
                      for c, l, rx in MEMO_CATS],
                other=[dict(memo=m, t=money(v)) for m, v in sorted(other_memos.items(), key=lambda kv: -abs(kv[1]))[:8] if v])


def payees_out(by_year, money):
    """The biggest payees across every year, by name order so a payee keeps its place, and what the
    rest came to each year -- written here so the page prints only the generator's figures."""
    tot = defaultdict(Decimal)
    for fy, ps in by_year.items():
        for p, x in ps.items():
            tot[p] += cents(x['v'])
    top = sorted(p for p, _ in sorted(tot.items(), key=lambda kv: -kv[1])[:PAYEE_TOP])
    rest = {}
    for fy, ps in by_year.items():
        r = sum((cents(x['v']) for p, x in ps.items() if p not in top), D0)
        if r:
            rest[fy] = dict(v=float(r), t=money(r))
    return dict(top=top, years=by_year, rest=rest)


def placement_counts(fys, fail):
    """CHILDREN PLACED OUT OF DISTRICT, 1 March, as each annual town report prints them
    (sources/data/placement-counts.csv, extract_placement_counts.py) -- for the group's years. A year
    whose report the archive does not hold is listed as not held, never as zero (rule 13c)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rows = {int(r['fy']): r for r in csv.DictReader(open(os.path.join(root, 'sources', 'data', 'placement-counts.csv'), encoding='utf-8'))}
    held = {}
    for r in csv.DictReader(open(os.path.join(root, 'sources', 'data', 'archive-manifest.csv'), encoding='utf-8')):
        m_ = re.match(r'town-annual-reports/docs/\d+-fy-(\d{4})-annual-town-report\.pdf$', r['key'])
        if m_:
            held[int(m_.group(1))] = '/docs/' + r['key']
    years_, missing = [], []
    for fy in fys:
        r = rows.get(fy)
        if not r or not r['collaborative']:
            missing.append(dict(fy='FY%d' % fy, held=fy in held))
            continue
        if r['parts_tie'] != 'yes':
            fail('placement counts FY%d: the parts do not tie to the stated total' % fy)
        years_.append(dict(fy='FY%d' % fy, as_of=r['as_of'], total=int(r['total']), collaborative=int(r['collaborative']),
                           day=int(r['day']), residential=int(r['residential']), page=int(r['page']),
                           href=held.get(fy)))
    return dict(years=years_, missing=missing, csv='/docs/data/placement-counts.csv')


def dump(d):
    return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


def orphans(out_dir, outs):
    """Item files on disk that this run does not write: a slug that no longer exists."""
    gone = []
    for sub in ('line', 'fund', 'group'):
        d = os.path.join(out_dir, sub)
        if os.path.isdir(d):
            gone += [os.path.join(d, f) for f in os.listdir(d)
                     if f.endswith('.json') and os.path.join(d, f) not in outs]
    return sorted(gone)
