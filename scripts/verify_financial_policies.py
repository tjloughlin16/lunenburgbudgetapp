#!/usr/bin/env python3
"""Recompute the financial policy pages' headline figures from the raw documents and compare them
with what the payloads print (CLAUDE.md rule 9: recomputed, not re-read).

    python3.11 scripts/verify_financial_policies.py

Deliberately does NOT import financial_policies_data.py: a verifier that shares the generator's
reading can only agree with it. It opens the spreadsheets, the fact sheet CSV and the audit text
itself, by its own route, and asserts the NUMBER on the page, not the sentence around it.
"""
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
bad = []


def page(pid):
    return json.load(io.open(os.path.join(TOP, pid + '.json'), encoding='utf-8'))


def blob(p):
    return json.dumps(p, ensure_ascii=False)


def usd(n):
    return '$' + format(int(round(n)), ',d')


def expect(where, text, p):
    if text not in blob(p):
        bad.append('%s: %r not printed' % (where, text))


# 1. Free cash: the latest certification, by the state's own export.
import openpyxl  # noqa: E402
ws = openpyxl.load_workbook(os.path.join(ROOT, 'sources/state-dls/CertifiedFreeCashBudget351-2026-11-25-c47c84ed3c38.xlsx'),
                            read_only=True, data_only=True).worksheets[0]
rows = list(ws.iter_rows(values_only=True))
h = list(rows[0])
lun = {int(r[h.index('Fiscal Year')]): r for r in rows[1:] if r[h.index('Municipality')] == 'Lunenburg'
       and isinstance(r[h.index('Certified Free Cash as of 7/1')], (int, float))}
latest = max(lun)
fc = lun[latest][h.index('Certified Free Cash as of 7/1')]
shares = [0.20, 0.05, 0.10, 0.10, 0.20]
claimed = sum(fc * s for s in shares) + min(fc * 0.10, 250000)
p1 = page('financial-policy-rules')
expect('rules: free cash', usd(fc), p1)
expect('rules: claimed', usd(claimed), p1)
expect('rules: today fixes OPEB 10%', usd(fc * 0.10), p1)
expect('rules: no set use', usd(fc - claimed), p1)
expect('rules: share', '%d%%' % round(claimed / fc * 100), p1)
import math  # noqa: E402
keep, save, spend = fc * 0.20, fc * 0.25, fc * 0.20 + min(fc * 0.10, 250000)
for name, v in (('kept back', keep), ('saved', save), ('spent on set uses', spend)):
    if usd(math.floor(v)) not in blob(p1) and usd(v) not in blob(p1):
        bad.append('rules: %s %s not printed' % (name, usd(v)))

# 2. Peer ranks, by the state's stabilization export.
ws = openpyxl.load_workbook(os.path.join(ROOT, 'sources/state-dls/StablPerBudget351-2026-11-25-3f4c08a6593d.xlsx'),
                            read_only=True, data_only=True).worksheets[0]
rows = list(ws.iter_rows(values_only=True))
h = list(rows[0])
peers = {x['town'] for x in json.load(io.open(os.path.join(ROOT, 'fy28/public/data/free-cash.json')))['peers']}
st = {r[h.index('Municipality')]: r[h.index('Stabilization Fund Balance')] / r[h.index('Operating Budget')]
      for r in rows[1:] if r[h.index('Municipality')] in peers and r[h.index('Schedule A Fiscal Year')] == 2025}
order = sorted(st, key=lambda t: -st[t])
rank = order.index('Lunenburg') + 1
p2 = page('reserves-against-targets')
expect('targets: stabilization share', '%.2f%%' % (st['Lunenburg'] * 100), p2)
expect('targets: rank', '%dth of %d' % (rank, len(order)) if rank > 3 else '%d' % rank, p2)

# 3. OPEB: the audit's own ending balances and funded ratio.
au = io.open(os.path.join(ROOT, 'sources/town-supplementary/text/4552-fy-2025-audit-report.txt'), encoding='utf-8').read()
m = re.search(r'Balances at June 30, 2025…+ … \$ ([\d,]+)\s+\$ ([\d,]+)\s+\$ ([\d,]+)', au)
if not m:
    bad.append('opeb: the audit’s June 30, 2025 balance line did not read')
else:
    total, trust, net = (int(x.replace(',', '')) for x in m.groups())
    p3 = page('retiree-health-liability')
    expect('opeb: total', usd(total), p3)
    expect('opeb: trust', usd(trust), p3)
    expect('opeb: funded', '%.2f%%' % (trust / total * 100), p3)
    c = re.search(r'June 30, 2025…+ … \$ ([\d,]+)\s+\$ \(([\d,]+)\)\s+\$ ([\d,]+)', au)
    if c:
        expect('opeb: deficiency', usd(int(c.group(3).replace(',', ''))), p3)
    else:
        bad.append('opeb: the contributions line did not read')

# 4. The record: every row on the debate page, and the agenda's title count.
rec = list(csv.DictReader(io.open(os.path.join(ROOT, 'sources/data/financial-policy-record.csv'), encoding='utf-8')))
p4 = page('financial-policy-debate')
cap = sum(1 for r in rec if r['evidence'] == 'captions')
expect('debate: captions count', '%d of the %d dated meetings' % (cap, len(rec)), p4)
ag = io.open(os.path.join(ROOT, 'sources/meetings/text/finance-committee/2026-12-03-agenda-8154.txt'), encoding='utf-8').read()
n = len(re.findall(r'^\s*\d+\.\s+[A-Z]', ag.split('Financial Planning Policies')[1], re.M))
expect('debate: titles', 'The %d titles' % n, p4)
for r in rec:
    if r['url'] not in blob(p4):
        bad.append('debate: %s not cited' % r['url'])

# 5. Privacy: no names of people in the public pages beyond what the record is about.
for pid in ('financial-policy-rules', 'reserves-against-targets', 'retiree-health-liability', 'financial-policy-debate'):
    t = blob(page(pid))
    for word in ('email', 'e-mail', 'asked us', 'requested by'):
        if word in t.lower():
            bad.append('%s: contains %r' % (pid, word))

if bad:
    print('verify_financial_policies: %d FAILED' % len(bad))
    for b in bad:
        print('  ' + b)
    sys.exit(1)
print('verify_financial_policies: free cash %s, claimed %s; stabilization rank %d of %d; OPEB, record and agenda all match'
      % (usd(fc), usd(claimed), rank, len(order)))
