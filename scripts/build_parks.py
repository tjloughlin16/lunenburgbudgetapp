"""Parks & Recreation: what the department is voted, what its own fund holds and has done
since FY2011, what the registration system took in, and what the grounds cost to keep.

    python3 scripts/build_parks.py           # write fy28/public/data/parks.json
    python3 scripts/build_parks.py --check   # fail if it no longer reproduces

TJ, 17 September 2026: "can you build a report for parks, under 'the town' for whatever
data you got." What we hold: the FY26 ledger and fund reports (evidence), the annual
reports' Park User Fees series FY2011-FY2023 (read, tied) and FY2024-FY2025 balances
(transcribed), MyRec's two FY2025 sales reports (a system printout, not the town's books),
and a grounds-maintenance bid (stated). Each is labelled on the page with what it is, and
the one thing they would combine into -- what the fees became on the books -- is exactly
what none of them establishes. That is a money-gaps row, not a sentence here.
"""
import argparse
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C                                           # noqa: E402
from conclusions import conclusion, emit, figure                  # noqa: E402

FINANCE = os.path.join(ROOT, 'fy28', 'public', 'data', 'finance.json')
MYREC = os.path.join(ROOT, 'sources', 'data', 'parks-myrec-sales-fy2025.csv')
BID = os.path.join(ROOT, 'sources', 'town-ledgers', 'purchase-orders', 'po-closed-fy2025-parks-grounds-bid.pdf')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'parks.json')
PARKS = ['Fitzgerald Field', 'McNally Field', 'Marshall Park', 'Memorial Park', 'Town Beach', 'Wallis Park']


def fail(msg):
    sys.stderr.write('build_parks: %s\n' % msg)
    sys.exit(1)


def bid():
    """The grounds bid's per-park year-one totals, off its own text layer, footed."""
    import pypdf
    t = pypdf.PdfReader(BID).pages[0].extract_text()
    m = re.search(r'Location Total\s+([\d\s]+)$', t, re.M)
    if not m:
        fail('the bid sheet’s Location Total line is not where it was')
    vals = [int(x) for x in m.group(1).split()]
    if len(vals) != len(PARKS):
        fail('the bid sheet lists %d location totals, expected %d' % (len(vals), len(PARKS)))
    rows = []
    for park, total in zip(PARKS, vals):
        rows.append(dict(park=park, year_one=total))
    # The mowing lines, for the two fields and the two parks that are mowed.
    mow = re.search(r'MowingTotal Cost\s+([\dN/A\s]+)$', t, re.M)
    mowing = [None if x == 'N/A' else int(x) for x in mow.group(1).split()] if mow else [None] * 6
    for r, mv in zip(rows, mowing):
        r['mowing'] = mv
    return rows, sum(vals)


def myrec():
    rows = list(csv.DictReader(io.open(MYREC, encoding='utf-8')))
    for r in rows:
        for k in ('res_count', 'nonres_count', 'total_count'):
            r[k] = int(r[k])
        for k in ('res_total', 'nonres_total', 'total'):
            r[k] = float(r[k])
    return rows


def sources():
    want = {
        'town-ledgers/account-details/parks-program-financials-fy2025-myrec.pdf': ('MyRec Program Sales Report, FY2025', 'the department’s registration system, by records request'),
        'town-ledgers/account-details/parks-membership-sales-fy2025-myrec.pdf': ('MyRec Membership Sales Report, FY2025', 'the same'),
        'town-ledgers/purchase-orders/po-closed-fy2025-parks-grounds-bid.pdf': ('Grounds-maintenance bid, year one from 1 July 2024', 'a contractor, by records request'),
        'town-ledgers/expenses/glytdbud-expense-fy2024-p13-gf-parks.pdf': ('FY2024 year-to-date budget report, Parks, with journal detail', 'MUNIS, by records request; image only'),
        'town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx': ('FY26 special-revenue report, 31 March 2026', 'MUNIS, by records request'),
        'town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx': ('FY26 year-end budget report, general fund', 'MUNIS, by records request'),
    }
    man = {r['key']: r for r in csv.DictReader(io.open(MANIFEST, encoding='utf-8'))}
    out = []
    for key, (t, pub) in want.items():
        r = man.get(key) or fail('%s is not in the manifest (rule 12)' % key)
        out.append(dict(path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']), url=r.get('upstream') or '',
                        docs_url='/docs/' + key, table=t, publisher=pub, note=''))
    return out


def build():
    fin = json.load(open(FINANCE, encoding='utf-8'))
    M = fin['measures']
    appro, fund, gift = M['gf-650'], M['sr-1500'], M['sr-1523']
    a, f = appro['current'], fund['current']
    series = [h for h in fund['history'] if h['grade'] == 'read']
    trans = [h for h in fund['history'] if h['grade'] == 'transcribed']
    first, last = series[0], series[-1]
    low = min(series, key=lambda h: h['closing'])
    sales = myrec()
    prog = [r for r in sales if r['report'] == 'program']
    mem = [r for r in sales if r['report'] == 'membership']
    prog_total = sum(r['total'] for r in prog)
    mem_total = sum(r['total'] for r in mem)
    prog_n = sum(r['total_count'] for r in prog)
    mem_n = sum(r['total_count'] for r in mem)
    nonres = sum(r['nonres_total'] for r in sales)
    all_total = prog_total + mem_total
    nonres_share = 100 * nonres / all_total
    nonres_n = sum(r['nonres_count'] for r in sales)
    all_n = prog_n + mem_n
    top = max(prog, key=lambda r: r['total'])
    bid_rows, bid_total = bid()
    bid_share = 100 * bid_total / a['revised']
    held_share = 100 * f['closing'] / a['revised']
    fy25 = [h for h in trans if h['fy'] == 2025][0]

    rows = [
        conclusion(
            id='the-parks-reserve',
            claim='The parks’ own fee fund held %s at 31 March 2026 — %s of the %s voted for the year.'
                  % (C.usd(f['closing']), C.pct(held_share, 0), C.usd(a['revised'])),
            so_what='Money the parks may spend without a vote; it took in %s and spent %s in nine months of FY2026.' % (C.usd(f['revenue']), C.usd(f['spent'])),
            figures={'held': figure(f['closing'], C.usd(f['closing']), 'in the Park Revolving Fund, 31 March 2026'),
                     'share': figure(held_share, C.pct(held_share, 0)), 'appro': figure(a['revised'], C.usd(a['revised'])),
                     'in': figure(f['revenue'], C.usd(f['revenue'])), 'out': figure(f['spent'], C.usd(f['spent'])),
                     'spent_appro': figure(a['expended'], C.usd(a['expended']))},
            figure='held', kind='measured', bearing='sizes',
            detail='The general fund voted the department %s for FY2026 as revised and %s of it was spent by year end (the FY26 year-end budget report, department 650). '
                   'Beside that, fund 1500 — programme and beach fees, kept in a revolving fund the department spends on the parks that raise them — carried %s at the end of March, '
                   'after %s in and %s out since July. A revolving balance is not a surplus the town can move: it is committed to the purpose that raised it, by the vote that created the fund.'
                   % (C.usd(a['revised']), C.usd(a['expended']), C.usd(f['closing']), C.usd(f['revenue']), C.usd(f['spent'])),
            basis='sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx, the row for fund 1500 (ACCOUNT BALANCE, REVENUE, EXPENDITURE, FUND BALANCE, credits shown as amounts, identity asserted); the FY26 year-end expense report, department 650 summed from its accounts.',
            not_shown='What the balance is spoken for, or what the last quarter of FY2026 did. The report stops at 31 March.',
            allow=('1500', '650', 'FY26', '2026', '31'),
        ),
        conclusion(
            id='the-fund-since-2011',
            claim='The fund stood at %s in FY%d, fell to %s in FY%d, and was %s by 30 June 2025.'
                  % (C.usd(first['closing']), first['fy'], C.usd(low['closing']), low['fy'], C.usd(fy25['closing'])),
            so_what='Thirteen years read and tied, two transcribed — and FY2025 does not chain to the FY26 opening.',
            figures={'first': figure(first['closing'], C.usd(first['closing']), 'in the fund at the end of FY%d' % first['fy']),
                     'low': figure(low['closing'], C.usd(low['closing'])), 'fy25': figure(fy25['closing'], C.usd(fy25['closing'])),
                     'last_read': figure(last['closing'], C.usd(last['closing'])), 'opening26': figure(f['opening'], C.usd(f['opening'])),
                     'first_fy': figure(first['fy'], 'FY%d' % first['fy']), 'low_fy': figure(low['fy'], 'FY%d' % low['fy'])},
            figure='fy25', kind='measured', bearing='sizes',
            detail='The annual reports print the fund as “Park User Fees” under Parks & Recreation: balance forward, receipts, disbursements and balance carried, FY2011 to FY2023, every year tying to the report’s own totals. '
                   'FY2023 closed at %s. The FY2024 and FY2025 reports print a balance only, transcribed here; FY2025’s %s is not the %s the FY26 report opens with, and nothing in the archive says why — an audit adjustment, an encumbrance, or a misread digit all fit.'
                   % (C.usd(last['closing']), C.usd(fy25['closing']), C.usd(f['opening'])),
            basis='sources/data/special-revenue-read.csv (fund “Park User Fees”, FY2011–FY2023); sources/data/special-revenue-funds.csv rows 1500 for FY2024 and FY2025, column v2; the FY26 report’s ACCOUNT BALANCE.',
            not_shown='Receipts and spending for FY2024 and FY2025: the reports for those years print a balance and no flow.',
            allow=('FY2011', 'FY2023', 'FY2024', 'FY2025', 'FY26', '2025', '30', '1500'),
        ),
        conclusion(
            id='what-myrec-took-in',
            claim='The registration system recorded %s in FY2025: %s programme places and %s beach passes.'
                  % (C.usd(all_total), C.num(prog_n), C.num(mem_n)),
            so_what='%s of it — %s — was paid by non-residents; the largest programme was %s at %s.' % (C.pct(nonres_share, 0), C.usd(nonres), top['program'].title(), C.usd(top['total'])),
            figures={'all': figure(all_total, C.usd(all_total), 'recorded by MyRec, 1 July 2024 to 30 June 2025'),
                     'prog_n': figure(prog_n, C.num(prog_n)), 'mem_n': figure(mem_n, C.num(mem_n)),
                     'nonres_share': figure(nonres_share, C.pct(nonres_share, 0)), 'nonres': figure(nonres, C.usd(nonres)),
                     'top': figure(top['total'], C.usd(top['total'])), 'prog_total': figure(prog_total, C.usd(prog_total)), 'mem_total': figure(mem_total, C.usd(mem_total)),
                     'nonres_n': figure(nonres_n, C.num(nonres_n)), 'all_n': figure(all_n, C.num(all_n)), 'prog_count': figure(len(prog), C.num(len(prog)))},
            figure='all', kind='measured', bearing='sizes',
            detail='Two printouts from MyRec, the system the department sells through, both footing to their own totals: %s across %s programmes, %s across four membership lines. '
                   'Non-residents were %s of %s registrations and paid %s. That is what the system recorded, not what reached the town’s books — the FY2025 fund report that would show the deposits is not in the archive, and the general fund’s REC FEES line was estimated at zero for FY2026.'
                   % (C.usd(prog_total), C.num(len(prog)), C.usd(mem_total), C.num(nonres_n), C.num(all_n), C.usd(nonres)),
            basis='sources/data/parks-myrec-sales-fy2025.csv, extracted by scripts/extract_parks_myrec.py from the two MyRec reports and checked against their printed totals.',
            not_shown='Refunds, waivers, or what the programmes cost to run — a sales report is the fee side only. And a 2024 season sold partly before 1 July 2024 is undercounted in this window.',
            allow=('2024', '2025', 'FY2025', 'FY2026', '1'),
        ),
        conclusion(
            id='what-the-grounds-cost',
            claim='Grounds upkeep at six parks was bid at %s a year — %s of what the department is voted.'
                  % (C.usd(bid_total), C.pct(bid_share, 0)),
            so_what='%s is Marshall Park alone. A bid is an offer; what was paid is in the ledger, not here.' % C.usd([r for r in bid_rows if r['park'] == 'Marshall Park'][0]['year_one']),
            figures={'bid': figure(bid_total, C.usd(bid_total), 'bid for year one of grounds maintenance, from 1 July 2024'),
                     'share': figure(bid_share, C.pct(bid_share, 0)), 'appro': figure(a['revised'], C.usd(a['revised'])),
                     **{'p_%d' % i: figure(r['year_one'], C.usd(r['year_one'])) for i, r in enumerate(bid_rows)}},
            figure='bid', kind='measured', bearing='sizes',
            detail='The bid sheet prices mowing, weeding, turf, clean-ups and infield work per park for the year from 1 July 2024: %s. The total is the sheet’s own six location totals summed. '
                   'It is a vendor’s figure (stated), and the FY2026 appropriation it is set against is %s.'
                   % ('; '.join('%s %s' % (r['park'], C.usd(r['year_one'])) for r in bid_rows), C.usd(a['revised'])),
            basis='sources/town-ledgers/purchase-orders/po-closed-fy2025-parks-grounds-bid.pdf, the Location Total line, read from the text layer and footed.',
            not_shown='Whether this bid was accepted, or what the town paid for grounds work in any year: the FY2024 Parks budget report with its journal detail is in the archive as an image and has not been read.',
            allow=('1', '2024', 'FY2026'),
        ),
    ]
    return dict(
        generated_by='scripts/build_parks.py',
        about='Parks & Recreation: what the department is voted, what its own fee fund holds and has done since FY2011, what the registration system took in for FY2025, and what a contractor bid to keep the grounds.',
        grain='DOLLARS from four kinds of document kept apart: the FY26 accounting printouts (evidence), the annual reports’ fund schedule (read and tied; FY2024–FY2025 transcribed), the registration system’s sales (a printout, not the books), and a bid (stated). Not what the parks cost all in.',
        as_of=dict(ledger='FY2026 year end (period 12), unaudited', fund=f['as_of'], myrec='1 July 2024 – 30 June 2025'),
        appropriation=dict(code='650', name=appro['name'], **{k: a[k] for k in ('original', 'revised', 'expended', 'encumbered', 'available', 'period')}),
        fund=dict(code='1500', name=fund['name'], current=f, history=fund['history']),
        gift=dict(code='1523', name=gift['name'], current=gift['current'], history=gift['history']),
        other_funds=[dict(id=i, name=M[i]['name'], kind=M[i]['kind'], current=M[i]['current']) for i in ('sr-1529', 'sr-1532', 'tr-8126', 'cp-3108')],
        myrec=dict(program=prog, membership=mem, program_total=round(prog_total, 2), membership_total=round(mem_total, 2), total=round(all_total, 2),
                   nonres_total=round(nonres, 2), nonres_share=round(nonres_share, 1), program_n=prog_n, membership_n=mem_n),
        bid=dict(rows=bid_rows, total=bid_total),
        sources=sources(),
        not_established=[
            'What the registration system’s %s became on the town’s books — which fund it was deposited to, and when. The FY2025 special-revenue report and fund 1500’s journal would say.' % C.usd(all_total),
            'Why the fund’s 30 June 2025 balance in the annual report (%s) is not the FY26 report’s opening balance (%s).' % (C.usd(fy25['closing']), C.usd(f['opening'])),
            'What the parks cost to keep in any year: the FY2024 budget report with its journal detail is held as an image and not yet read; FY2025’s is not held.',
            'Whether the grounds bid was accepted.',
        ],
        conclusions=emit('parks', rows),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    text = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            fail('%s is stale' % os.path.relpath(OUT, ROOT))
        print('parks.json reproduces: %d conclusions' % len(data['conclusions']))
        return
    open(OUT, 'w', encoding='utf-8').write(text)
    print('wrote %s: %d conclusions' % (os.path.relpath(OUT, ROOT), len(data['conclusions'])))


if __name__ == '__main__':
    main()
