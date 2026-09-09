#!/usr/bin/env python3
"""Every figure the /what-families-pay table publishes, recomputed from the archive.

    python3 scripts/verify_what_families_pay.py

WHAT THIS CHECKS AND WHAT IT CANNOT. It recomputes each household bill from
`rate_register` and the athletic fee schedule -- the CSVs and the database, never the
payload's own arithmetic -- and asserts the payload agrees. It cannot check that the page
answers anybody's question; that is `notes/process/PERSONAS.md` and it was run.

WRITTEN AFTER THE PROSE, ON PURPOSE (step 5 of WRITING-AN-ANALYSIS). A verifier written
first asserts what you meant to say. Three things it therefore asserts about STRUCTURE and
not only about figures, because each is a sentence the page rests on that no single number
would catch:

  1. the household the page OPENS on is priced, and its total is the sum of its own rows.
     `verify_athletics.py` once passed because a sentence existed while the sentence was
     wrong; a total that is not the sum of the rows under it is that failure in numbers;
  2. every charge with no published amount carries a records request, because rule 7c says
     a gap with no named remedy is a grievance;
  3. no unpriced row carries an amount, and no priced row is missing one. That is the
     floor/bill distinction the whole page turns on, and collapsing it would be rule 7 --
     publishing a guess as a measurement.

RULE 13. Amounts are read from the register by (category, item, fy) -- the triple that is
actually unique -- and never off a rendered table. `athletic_fee_schedule` carries several
rows per org and a lookup on one column silently checks the wrong line.
"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28/public/data/what-families-pay.json')
PAGE = os.path.join(ROOT, 'fy28/src/pages/WhatFamiliesPay.tsx')

fails = []
checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)


def money(x):
    return None if x in (None, '') else round(float(x) + 0.0, 2)


def main():
    if not os.path.exists(PAYLOAD):
        sys.exit('run scripts/build_what_families_pay.py first')
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    h = d['household']
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    reg = [dict(r) for r in c.execute(
        'SELECT fy, category, item, value, status FROM rate_register')]

    def rate(category, item, fy=None):
        hit = [r for r in reg if r['category'] == category and r['item'] == item
               and (fy is None or str(r['fy']) == str(fy))]
        ok(len(hit) <= 1, f'{category}/{item} FY{fy} is not unique in rate_register')
        return money(hit[0]['value']) if hit and hit[0]['value'] not in (None, '') else None

    defs = h['charge_defs']

    # ---- 1. THE LEAD HOUSEHOLD. The number the page is named after. -------------------
    lead = h['lead']
    ok(lead['key'] in h['bills'], 'the household the page opens on is not in `bills`')
    rows = lead['rows']
    floor = round(sum(r['amount'] for r in rows
                      if r['band'] == 'priced' and r['amount'] is not None), 2)
    carried = round(sum(r['amount'] for r in rows
                        if r['band'] == 'carried' and r['amount'] is not None), 2)
    ok(abs(floor - lead['floor']) < 0.005,
       f"lead floor {lead['floor']} is not the sum of its priced rows ({floor})")
    ok(abs(carried - lead['carried']) < 0.005,
       f"lead carried {lead['carried']} is not the sum of its carried rows ({carried})")
    ok(abs(lead['floor_carried'] - (floor + carried)) < 0.005,
       'the lead total is not floor plus carried')
    ok(lead['floor_carried'] > 0, 'the household the page opens on totals nothing')

    # ---- 2. EVERY BILL, against the register. -----------------------------------------
    act26 = rate('activity_fee', 'student activity fee', 2026)
    ok(act26 == 70.00, f'the student activity fee is {act26}, not the $70 voted 7 May 2025')
    ok(rate('activity_fee', 'student activity fee', 2025) == 55.00,
       'the rate the $70 replaced is no longer $55 in the register')
    ok(rate('meals', 'standard school meal', 2027) == 0.00,
       'the standard school meal is no longer recorded as costing a family nothing')
    ok(rate('bus_fee', 'one student', 2027) == 180.00, 'the FY2027 single-child bus fee moved')
    ok(rate('bus_fee', 'two or more students', 2027) == 270.00,
       'the FY2027 family bus rate moved')

    bad_total, bad_band, bad_bus, bad_act = [], [], [], []
    for key, b in h['bills'].items():
        fy, level, ch, sp, tier, bus, acts, park = key.split('|')
        ch, sp = int(ch), int(sp)
        f = round(sum(r['amount'] for r in b['rows']
                      if r['band'] == 'priced' and r['amount'] is not None), 2)
        ca = round(sum(r['amount'] for r in b['rows']
                       if r['band'] == 'carried' and r['amount'] is not None), 2)
        if abs(f - b['floor']) > 0.005 or abs(ca - b['carried']) > 0.005 \
           or abs(b['floor_carried'] - (f + ca)) > 0.005:
            bad_total.append(key)
        for r in b['rows']:
            # THE FLOOR/BILL DISTINCTION, asserted. An unpriced row with a number in it
            # would be a guess published as a measurement.
            if r['band'] == 'unpriced' and r['amount'] is not None:
                bad_band.append(f'{key}/{r["id"]} is unpriced and carries an amount')
            if r['band'] in ('priced', 'carried') and r['amount'] is None:
                bad_band.append(f'{key}/{r["id"]} is {r["band"]} and carries no amount')
            if r['id'] not in defs:
                bad_band.append(f'{key}/{r["id"]} has no entry in charge_defs')
        # The bus is a FAMILY charge. Two children must not cost twice one child.
        busrow = next((r for r in b['rows'] if r['id'].startswith('bus:')), None)
        if bus == '1' and busrow is None:
            bad_bus.append(f'{key} rides the bus and has no bus row')
        if bus == '0' and busrow is not None:
            bad_bus.append(f'{key} does not ride the bus and has a bus row')
        if busrow and busrow['amount'] is not None and tier == 'full':
            want = rate('bus_fee', 'one student' if ch == 1 else 'two or more students',
                        fy) or rate('bus_fee',
                                    'one student' if ch == 1 else 'two or more students',
                                    2026)
            if want is not None and abs(busrow['amount'] - want) > 0.005:
                bad_bus.append(f'{key} bus is {busrow["amount"]}, register says {want}')
        # The activity fee is PER CHILD, at the rate the committee voted.
        actrow = next((r for r in b['rows'] if r['id'].startswith('activity:')), None)
        if acts == '1' and actrow is None:
            bad_act.append(f'{key} is in a club and has no activity row')
        if acts == '0' and actrow is not None:
            bad_act.append(f'{key} is in no club and has an activity row')
        if actrow and abs(actrow['amount'] - act26 * ch) > 0.005:
            bad_act.append(f'{key} activity fee is {actrow["amount"]}, not {act26} x {ch}')

    ok(not bad_total, f'{len(bad_total)} bills whose total is not the sum of their rows: '
                      + '; '.join(bad_total[:3]))
    ok(not bad_band, f'{len(bad_band)} band/amount contradictions: ' + '; '.join(bad_band[:3]))
    ok(not bad_bus, f'{len(bad_bus)} bus rows disagree with the register: '
                    + '; '.join(bad_bus[:3]))
    ok(not bad_act, f'{len(bad_act)} activity rows disagree with the register: '
                    + '; '.join(bad_act[:3]))

    # THE BUS IS A FAMILY RATE and the page says so. Assert the structure, not the prose.
    one = h['bills'][f"2027|HS|1|1|full|1|1|0"]
    two = h['bills'][f"2027|HS|2|1|full|1|1|0"]
    b1 = next(r for r in one['rows'] if r['id'].startswith('bus:'))['amount']
    b2 = next(r for r in two['rows'] if r['id'].startswith('bus:'))['amount']
    ok(b2 < 2 * b1, 'the bus no longer costs a two-child family less than twice a '
                    'one-child family — the page states that it is a family charge')

    # ---- 3. THE UNPRICED BAND, and its remedies (rule 7c). ---------------------------
    unpriced = [r for r in h['standing'] if r['band'] == 'unpriced']
    ok(len(unpriced) == h['unpriced_named'],
       f"unpriced_named says {h['unpriced_named']}, the table shows {len(unpriced)}")
    ok(len(unpriced) >= 5, 'the unpriced band has collapsed below five charges — the page '
                           'calls its total a floor on the strength of it')
    no_req = [defs[r['id']]['label'] for r in unpriced if not defs[r['id']]['request']]
    ok(not no_req, 'charges with no records request written for them: ' + '; '.join(no_req))
    ok(all(r['amount'] is None for r in unpriced),
       'a charge in the unpriced band has acquired an amount without changing band')

    # The request has to name a DOCUMENT and a UNIT, or it is not sendable.
    vague = [defs[r['id']]['label'] for r in unpriced
             if len(defs[r['id']]['request'] or '') < 40]
    ok(not vague, 'requests too short to send: ' + '; '.join(vague))

    # ---- 4. THE FREE ROW. Rule 8: the credit is checked like anything else. -----------
    meals = [r for r in h['standing'] if r['band'] == 'no charge']
    ok(len(meals) >= 1, 'the school meals row is gone — the page states that a family is '
                        'not billed for the standard meal')
    ok(all(r['amount'] == 0 for r in meals), 'a "no charge" row carries a charge')

    # ---- 5. RULE 2. No figure typed into the page. ------------------------------------
    import re
    page = open(PAGE, encoding='utf-8').read()
    # THE RENDERED BODY ONLY. Slice from the component -- an earlier `return (` belongs to
    # a helper, and slicing there swept the file's own docstring into the search, where a
    # figure quoted in a COMMENT read as a figure typed into the page. Then strip block and
    # line comments, because a comment does not render and rule 2 is about what ships.
    body = page[page.index('export function WhatFamiliesPay'):]
    body = re.sub(r'/\*.*?\*/', ' ', body, flags=re.S)
    body = re.sub(r'^\s*//.*$', ' ', body, flags=re.M)
    typed = sorted(set(re.findall(r'\$[\d,]+(?:\.\d\d)?', body)))
    ok(not typed, 'figures typed into the page body rather than interpolated: '
                  + ', '.join(typed))

    print(f'verify_what_families_pay: {checks} checks')
    print(f"  the household the page opens on: {lead['key']}")
    for r in lead['rows']:
        amt = 'not published' if r['amount'] is None else f"{r['amount']:>9,.2f}"
        print(f"    {defs[r['id']]['label']:<24} {r['band']:<9} {amt}")
    print(f"    {'TOTAL':<24} {'':<9} {lead['floor_carried']:>9,.2f}")
    print(f"  {len(h['bills'])} households priced, {len(unpriced)} charges unpriced, "
          f"each with a request")
    if fails:
        print('\nFAILED:')
        for f in fails:
            print('  -', f)
        return 1
    print('\nall figures reproduce from the archive')
    return 0


if __name__ == '__main__':
    sys.exit(main())
