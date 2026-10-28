"""THE WEB OF A YEAR: every fund and every school line as a block, and an arrow for each way money
connected them (fy-breakdown). TJ, 28 October 2026: "every school line is a block. every fund /
source of money is a block. then draw directional lines between them for the year that show the
relationships of how they connect (re-charges, pays, etc). I want to see the web of how the
accounts are paying for things across the school department."

EVERY ARROW IS A PLACEMENT THE MODEL ALREADY MADE (fy_breakdown.model()['src']), so the web adds
no reading of its own and its arrows sum to what each fund spent, to the cent (asserted):

    paid      fund -> line      the fund paid toward the line from the start (OUR match: same payee)
    later     fund -> line      the school budget paid, then re-charged the bill to the fund
                                (the books name both ends)
    back      line -> fund      the reverse: a bill moved back onto the school budget
    kind      fund -> category  same kind of work, by function code (OUR match), never one line
    none      fund -> no line   spending the books give no school line
    capital   fund -> capital   a capital article's own project
    between   fund -> between   moved from one fund to another by journal entry
    school    school -> line    the school budget's own spending on the line, after re-charges
    transfer  line -> line      budget moved between two lines (BUA), where one side is one line,
                                so the pairing is the books' and not ours. Budget, not spending.

The books never record which line's leftover paid for another line's overrun (the budget is one
pool), so there are no line-to-line arrows of spending, and the web does not invent any.

Written as /data/fy-breakdown/web-<year>.json, fetched for the year shown.
"""
import json
import os
from collections import defaultdict
from decimal import Decimal

import journal as J

D0 = Decimal(0)
SINKS = [('none', 'No school line'), ('capital', 'Capital articles'), ('between', 'Moved between funds')]


def files(m, line_name, fund_label, fund_group, payer_group, cat_label, money, out_dir, fail):
    A = J.accounts()
    out = {}
    for fy in J.YEARS:
        rows = [r for r in m['rows'] if r['fy'] == fy]
        nodes, edges = {}, []
        lines = {r['account']: r for r in rows if r['account']}

        def line(acct):
            k = 'l:' + acct
            if k not in nodes:
                r = lines[acct]
                nodes[k] = dict(id=k, kind='line', label=line_name(r), cat=cat_label[r['category']],
                                cid=r['category'])
            return k

        def edge(a, b, kind, v):
            if round(v, 2):
                edges.append(dict(a=a, b=b, k=kind, v=round(float(v), 2), t=money(v)))

        nodes['f:school'] = dict(id='f:school', kind='fund', label='School budget', group='gf',
                                 sub='School general fund, department 300')
        for r in lines.values():
            edge('f:school', line(r['account']), 'school', r['gf_spent'] - r['other_year_spent'])
        spent = defaultdict(Decimal)
        for (y, f), d in sorted(m['src'].items()):
            if y != fy:
                continue
            fk = 'f:' + f
            nodes[fk] = dict(id=fk, kind='fund', label=fund_label(f, A),
                             group=payer_group(fund_group(m, A, fy, f)), sub=f)
            for (kind, dest), v in d.items():
                spent[fk] += v
                if kind == 'payee':
                    edge(fk, line(dest), 'paid', v)
                elif kind == 'later':
                    edge(fk, line(dest), 'later', v)
                elif kind == 'back':
                    # a bill moved back onto the school budget: the school line took it from the fund
                    edge(line(dest), fk, 'back', -v)
                elif kind == 'function':
                    ck = 'k:' + dest
                    nodes.setdefault(ck, dict(id=ck, kind='line', label='%s, same kind of work' % cat_label[dest],
                                              cat=cat_label[dest], cid=dest, sub='by function code'))
                    edge(fk, ck, 'kind', v)
                elif kind in ('none', 'capital', 'between'):
                    sk = 'x:' + kind
                    nodes.setdefault(sk, dict(id=sk, kind='sink', label=dict(SINKS)[kind]))
                    # money moved between funds is in on one fund and out on another; the arrow
                    # carries its size, the direction is in the fund's own popup
                    edge(fk, sk, kind if kind != 'between' else 'between', abs(v) if kind == 'between' else v)
                else:
                    fail('FY%d fund %s: a placement of kind %r the web does not draw' % (fy, f, kind))
        # EVERY PLACEMENT IS AN ARROW, and only once: the drawn amounts (back reversed, between
        # by size) are each fund's spending, to the cent
        drawn = defaultdict(Decimal)
        for e in edges:
            if e['k'] == 'school':
                continue
            fk = e['b'] if e['k'] == 'back' else e['a']
            drawn[fk] += Decimal(e['t'].replace('$', '').replace(',', '')) * (-1 if e['k'] == 'back' else 1)
        for fk, v in spent.items():
            between = sum((dv for (kind, _), dv in m['src'][(fy, fk[2:])].items() if kind == 'between'), D0)
            want = v - between + sum((abs(dv) for (kind, _), dv in m['src'][(fy, fk[2:])].items()
                                      if kind == 'between' and round(dv, 2)), D0)
            if abs(drawn[fk] - want) > Decimal('0.01') * len(m['src'][(fy, fk[2:])]):
                fail('FY%d %s: its arrows carry %s, it placed %s' % (fy, fk, drawn[fk], want))
        # budget transfers with one line on a side: the pairing is the books'
        for t in m['transfers']:
            if t['fy'] != fy:
                continue
            if len(t['gave']) == 1:
                for g in t['got']:
                    if g['account'] in lines and t['gave'][0]['account'] in lines:
                        edges.append(dict(a=line(t['gave'][0]['account']), b=line(g['account']), k='transfer',
                                          v=round(float(g['amount']), 2), t=money(g['amount']), d=t['date'],
                                          m=t['description']))
            elif len(t['got']) == 1:
                for g in t['gave']:
                    if g['account'] in lines and t['got'][0]['account'] in lines:
                        edges.append(dict(a=line(g['account']), b=line(t['got'][0]['account']), k='transfer',
                                          v=round(float(-g['amount']), 2), t=money(-g['amount']), d=t['date'],
                                          m=t['description']))
        # every line with a budget is a block, connected or not: the toggle shows them
        for r in lines.values():
            line(r['account'])
        out[os.path.join(out_dir, 'web-%d.json' % fy)] = json.dumps(
            dict(fy=fy, nodes=sorted(nodes.values(), key=lambda n: n['id']), edges=edges),
            ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
    return out
