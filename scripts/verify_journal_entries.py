#!/usr/bin/env python3
"""VERIFY THE JOURNAL ENTRIES PAGE: every figure it prints, recomputed from the raw journal lines.

    python3.11 scripts/verify_journal_entries.py     # exits 1 on any mismatch

Rule 9: recomputed, not re-read. This script does NOT import journal.py, journal_join.py or the
page generator. It reads three files with the csv module:
  * sources/data/munis-school-journal.csv  -- the raw lines, the only source of an amount here;
  * sources/data/munis-school-journal-entries.csv -- only for WHICH lines form an entry, its kind
    and its chain (the join's classification), never for an amount;
  * sources/data/journal-entry-flags.csv -- only for which entries a rule flagged.
and asserts, against fy28/public/data/topics/journal-entries.json:
  1. the entries file holds every GEN/GRV line once, and each entry's debits, credits and net
     equal its raw lines to the cent;
  2. each chain's net equals the raw lines of its entries plus the journal it reverses;
  3. every figure the page registers -- finding, facts, conclusions -- equals the value
     recomputed here, by year: accruals, money with its other side outside the school books,
     the health insurance share of it, and the dollars citing a date after the close.
"""
import csv
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
D0 = Decimal(0)
bad = []


def check(ok, msg):
    if not ok:
        bad.append(msg)


raw = list(csv.DictReader(open(os.path.join(DATA, 'munis-school-journal.csv'), encoding='utf-8')))
ent = list(csv.DictReader(open(os.path.join(DATA, 'munis-school-journal-entries.csv'), encoding='utf-8')))
flags = list(csv.DictReader(open(os.path.join(DATA, 'journal-entry-flags.csv'), encoding='utf-8')))
page = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', 'journal-entries.json'),
                      encoding='utf-8'))

# ---- 1. lines -> entries, by (journal, description)
groups = defaultdict(list)
by_journal = defaultdict(list)
for r in raw:
    r['amt'] = Decimal(r['amount'])
    by_journal[(r['fiscal_year'], r['journal'])].append(r)
    if r['source'] in ('GEN', 'GRV'):
        groups[(r['fiscal_year'], r['journal'], r['description'])].append(r)
owner = {}
for e in ent:
    for d in json.loads(e['descriptions']):
        k = (e['fiscal_year'], e['journal'], d)
        check(k not in owner, 'description group %s is in two entries' % (k,))
        owner[k] = e['entry']
check(set(owner) == set(groups), 'entries cover %d description groups; the journal has %d'
      % (len(owner), len(groups)))
lines_of = defaultdict(list)
for k, ls in groups.items():
    lines_of[(k[0], owner.get(k))].extend(ls)
n_raw = sum(len(v) for v in groups.values())
check(sum(int(e['lines']) for e in ent) == n_raw, 'entries hold %d lines; raw GEN/GRV %d'
      % (sum(int(e['lines']) for e in ent), n_raw))
for e in ent:
    ls = lines_of[(e['fiscal_year'], e['entry'])]
    check(len(ls) == int(e['lines']), '%s: %d lines, raw %d' % (e['entry'], int(e['lines']), len(ls)))
    dr = sum((l['amt'] for l in ls if l['amt'] > 0), D0)
    cr = -sum((l['amt'] for l in ls if l['amt'] < 0), D0)
    check(dr == Decimal(e['debits']) and cr == Decimal(e['credits'])
          and dr - cr == Decimal(e['net']), '%s: debits/credits/net differ from its raw lines' % e['entry'])

# ---- 2. chains
net_of = {(e['fiscal_year'], e['entry']): sum((l['amt'] for l in lines_of[(e['fiscal_year'], e['entry'])]), D0)
          for e in ent}
ids = {(e['fiscal_year'], e['entry']) for e in ent}
chains = defaultdict(set)
for e in ent:
    chains[(e['fiscal_year'], e['chain'])].add((e['fiscal_year'], e['entry']))
    if e['pairs_with']:
        chains[(e['fiscal_year'], e['chain'])].add((e['fiscal_year'], e['pairs_with']))
chain_net = {}
for c, ms in chains.items():
    tot = D0
    for m in ms:
        tot += net_of[m] if m in ids else sum((l['amt'] for l in by_journal[m]), D0)
    chain_net[c] = tot
for e in ent:
    check(chain_net[(e['fiscal_year'], e['chain'])] == Decimal(e['chain_net']),
          '%s: chain net %s, raw %s' % (e['entry'], e['chain_net'], chain_net[(e['fiscal_year'], e['chain'])]))


# ---- 3. the page's figures
def one_sided(e):
    if e['chain'] != e['entry']:
        return D0
    return abs(chain_net[(e['fiscal_year'], e['chain'])])


years = sorted({int(e['fiscal_year']) for e in ent})
acc = {y: sum((one_sided(e) for e in ent if int(e['fiscal_year']) == y and e['kind'] == 'payroll accrual'), D0)
       for y in years}
outside = {y: sum((one_sided(e) for e in ent if int(e['fiscal_year']) == y
                   and e['kind'] not in ('payroll accrual', 'town charge')), D0) for y in years}
last, prev = years[-1], years[-2]
health = sum((one_sided(e) for e in ent if int(e['fiscal_year']) == last
              and e['kind'] not in ('payroll accrual', 'town charge')
              and all(l['object'] in ('570001', '570008') for l in lines_of[(e['fiscal_year'], e['entry'])])), D0)
after_ids = {(f['fiscal_year'], f['entry']) for f in flags if f['rule'] == 'after'}
after = {}
for y in years:
    tot = D0
    for e in ent:
        if (e['fiscal_year'], e['entry']) in after_ids and int(e['fiscal_year']) == y:
            ls = lines_of[(e['fiscal_year'], e['entry'])]
            moved = min(sum((l['amt'] for l in ls if l['amt'] > 0), D0),
                        -sum((l['amt'] for l in ls if l['amt'] < 0), D0))
            tot += moved + one_sided(e)
    after[y] = tot
top = max((y for y in years if y != last), key=lambda y: after[y])

want = {  # fact id -> value recomputed here
    'acclo': min(acc.values()), 'acchi': max(acc.values()),
    'outl': outside[last], 'outp': outside[prev],
    'aft': after[top], 'aftn': sum(1 for i in after_ids if int(i[0]) == top),
}
facts = {}
for b in page['blocks']:
    for c in b.get('claims', []):
        for f in c['facts']:
            facts[f['id']] = f
for k, v in want.items():
    check(k in facts, 'fact %s is not on the page' % k)
    if k in facts:
        got = Decimal(str(facts[k]['value']['value']))
        check(abs(got - Decimal(v)) < Decimal('0.005'), 'fact %s: page %s, recomputed %s' % (k, got, v))
fig = page['finding']['figures']
check(abs(Decimal(str(fig['a']['value'])) - outside[last]) < Decimal('0.005'), 'finding: outside %s' % fig['a'])
check(abs(Decimal(str(fig['b']['value'])) - outside[prev]) < Decimal('0.005'), 'finding: prior %s' % fig['b'])
hs = [c for b in page['blocks'] for c in b.get('claims', []) if 'Health insurance' in c.get('so', {}).get('text', '')]
check(len(hs) == 1 and abs(Decimal(str(hs[0]['so']['figures']['h']['value'])) - health) < Decimal('0.005'),
      'health insurance share: recomputed %s' % health)
check(health > outside[last] / 2, 'health insurance is not most of the newest year (%s of %s)' % (health, outside[last]))

if bad:
    print('verify_journal_entries: %d FAILED' % len(bad))
    for b in bad[:40]:
        print('  ' + b)
    sys.exit(1)
print('verify_journal_entries: %d entries, %d lines tie to the raw journal; %d chains; %d page figures '
      'recomputed and equal (outside %s %s, %s %s; accruals %s-%s; health %s; after-close %s %s)'
      % (len(ent), n_raw, len(chains), len(want) + 3, last, outside[last], prev, outside[prev],
         min(acc.values()), max(acc.values()), health, top, after[top]))
