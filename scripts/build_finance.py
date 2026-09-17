"""Every accounting measure, by the board or department that owns it, with what it holds
now and what it has done over time -- the payload behind /accounts, /departments/<slug>
and /boards/<slug>/finance.

    python3 scripts/build_finance.py           # write fy28/public/data/finance.json
    python3 scripts/build_finance.py --check   # fail if it no longer reproduces

The registry (sources/data/fund-owners.csv, kept complete by build_fund_owners.py) says
what the measures are and who owns them. This script puts the figures beside each one,
and it keeps three grades of figure apart on the page the way rule 13a asks:

    evidence      a MUNIS printout: the FY26 ledger (period 9 and the year-end period 12),
                  the FY26 special-revenue report and the FY26 trust report, all as of the
                  date each one states
    read          the annual reports' special-revenue schedule FY2011-FY2023, read off the
                  page and tied to the printed totals (special-revenue-read.csv)
    transcribed   the annual reports' balance tables for FY2023-FY2025, OCR, columns read
                  by position and chained to the FY26 opening balance where they chain

Nothing here averages the three or fills a gap between them. FY2024 and FY2025 special-
revenue activity is a records request (money-gaps.csv), and the page says so.

The School Committee's page carries conclusions; they are drawn from the FY26 report only.
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
from build_fund_owners import (REG, DEPTS, BOARDS, LEDGER, SPECIAL, TRUST,  # noqa: E402
                               owners as owner_table, read as read_registry)

SR_READ = os.path.join(ROOT, 'sources', 'data', 'special-revenue-read.csv')
SR_OCR = os.path.join(ROOT, 'sources', 'data', 'special-revenue-funds.csv')
TRUST_OCR = os.path.join(ROOT, 'sources', 'data', 'report-trust-funds.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'finance.json')


def fail(msg):
    sys.stderr.write('build_finance: %s\n' % msg)
    sys.exit(1)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def r2(v):
    return None if v is None else round(v, 2)


# --- the FY26 printouts ------------------------------------------------------------------

def ledger():
    """General-fund departments (period 9 as printed; period 12 summed from its accounts),
    revenue accounts (period 9), enterprise funds (period 9, summed)."""
    rows = list(csv.DictReader(io.open(LEDGER, encoding='utf-8')))
    depts, revenue, ent = {}, {}, {}
    for r in rows:
        snap = dict(fy=int(r['fy']), period=int(r['period']), original=num(r['original']),
                    revised=num(r['revised']), expended=num(r['expended']),
                    encumbered=num(r['encumbered']), available=num(r['available']), report=r['doc_id'])
        if r['fund'] == '0100' and r['level'] == 'department':
            depts.setdefault(r['dept'], {})[snap['period']] = snap
        elif r['fund'] == '0100' and r['level'] == 'account' and r['account_type'] == 'expense':
            d = depts.setdefault(r['dept'], {})
            s = d.setdefault(snap['period'], dict(snap, original=0.0, revised=0.0, expended=0.0, encumbered=0.0, available=0.0, summed=0))
            for k in ('original', 'revised', 'expended', 'encumbered', 'available'):
                s[k] = round(s[k] + (snap[k] or 0), 2)
            s['summed'] += 1
        elif r['fund'] == '0100' and r['account_type'] == 'revenue':
            # MUNIS prints revenue as credits, negative. Shown as amounts.
            revenue[r['object']] = dict(fy=snap['fy'], period=snap['period'],
                                        estimate=r2(-(snap['revised'] or 0)), collected=r2(-(snap['expended'] or 0)),
                                        report=r['doc_id'])
        elif r['fund'] != '0100':
            e = ent.setdefault(r['fund'], dict(fy=snap['fy'], period=snap['period'], expense_budget=0.0, expended=0.0,
                                               revenue_estimate=0.0, collected=0.0, reports=set()))
            e['reports'].add(r['doc_id'])
            if r['account_type'] == 'expense':
                e['expense_budget'] = round(e['expense_budget'] + (snap['revised'] or 0), 2)
                e['expended'] = round(e['expended'] + (snap['expended'] or 0), 2)
            else:
                e['revenue_estimate'] = round(e['revenue_estimate'] - (snap['revised'] or 0), 2)
                e['collected'] = round(e['collected'] - (snap['expended'] or 0), 2)
    for e in ent.values():
        e['reports'] = sorted(e['reports'])
    return depts, revenue, ent


def special():
    """Every fund on the FY26 special-revenue report, by the arithmetic identity -- see
    build_youth_sports.fy26_funds, which this generalises. A fund that does not foot is
    kept, flagged, and its closing balance shown alone."""
    import openpyxl
    ws = openpyxl.load_workbook(SPECIAL, read_only=True, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = {str(v).strip(): i for i, v in enumerate(rows[6]) if v}
    asof = str(rows[3][0])[:10]
    out = {}
    for r in rows[7:]:
        f = r[hdr['FUND']]
        if isinstance(f, str) and f.strip("' ").isdigit():
            f = int(f.strip("' "))
        if not isinstance(f, (int, float)):
            continue
        f = str(int(f))
        if f in out:
            continue
        opening = -(num(r[hdr['ACCOUNT BALANCE']]) or 0)
        revenue = -(num(r[hdr['REVENUE']]) or 0)
        salaries = num(r[hdr['SALARIES']]) or 0
        expenditure = num(r[hdr['EXPENDITURE']]) or 0
        encumbered = num(r[hdr['ENCUMBRANCE']]) or 0
        closing = -(num(r[hdr['FUND BALANCE']]) or 0)
        foots = abs(opening + revenue - salaries - expenditure - closing) <= 0.02
        out[f] = dict(fy=2026, as_of=asof, opening=r2(opening), revenue=r2(revenue), spent=r2(salaries + expenditure),
                      salaries=r2(salaries), encumbered=r2(encumbered), closing=r2(closing), foots=foots,
                      report=os.path.relpath(SPECIAL, ROOT))
    return out, asof


def trusts():
    import openpyxl
    ws = openpyxl.load_workbook(TRUST, read_only=True, data_only=True)['Sheet2']
    rows = list(ws.iter_rows(values_only=True))
    asof = str(rows[2][0])[:10]
    labels = [str(v).strip() for v in rows[4] if v]
    if labels != ['Beginning', 'Revenue', 'Expenditure', 'Remaining']:
        fail('the trust report’s header row has changed: %r' % labels)
    out = {}
    for r in rows:
        if not isinstance(r[0], (int, float)) or not isinstance(r[1], str):
            continue
        code = str(int(r[0]))
        # Balances print as credits (negative); the two agency accounts that hold a debit
        # print positive. Shown as the amount held, sign preserved.
        out[code] = dict(fy=2026, as_of=asof, opening=r2(-(num(r[3]) or 0)), revenue=r2(-(num(r[5]) or 0)),
                         spent=r2(num(r[6]) or 0), closing=r2(-(num(r[8]) or 0)),
                         report=os.path.relpath(TRUST, ROOT))
        o = out[code]
        o['foots'] = abs(o['opening'] + o['revenue'] - o['spent'] - o['closing']) <= 0.02
    return out, asof


# --- the annual reports ------------------------------------------------------------------

def sr_read_history():
    """FY2011-FY2023, by the name the annual report used, from the page-read dataset."""
    by = {}
    for r in csv.DictReader(io.open(SR_READ, encoding='utf-8')):
        by.setdefault(r['fund'].strip(), []).append(dict(
            fy=int(r['fy']), opening=num(r['forward']), revenue=num(r['receipts']), spent=num(r['disbursements']),
            closing=num(r['carried']), grade='read', report=r['document']))
    return by


def sr_ocr_balances():
    """FY2024 and FY2025 closing balances, by fund code, from the OCR extract of the annual
    reports' balance tables. The column is read by position (v2 = Fund Balance 6/30), which
    the FY2024 page confirms for fund 1306; each figure is checked against the FY26 opening
    balance where the years chain."""
    out = {}
    for r in csv.DictReader(io.open(SR_OCR, encoding='utf-8')):
        if r['fy'] not in ('2024', '2025'):
            continue
        m = re.match(r"^\s*'?(\d{4})\s", r['fund'] or '')
        if not m:
            continue
        v = num(r['v2'])
        if v is None:
            continue
        out.setdefault(m.group(1), {})[int(r['fy'])] = v
    return out


def trust_ocr_balances():
    out = {}
    for r in csv.DictReader(io.open(TRUST_OCR, encoding='utf-8')):
        if r['kind'] != 'row' or r['fy'] not in ('2023', '2024', '2025'):
            continue
        m = re.match(r'^\s*(\d{4})\s', r['label'] or '')
        if not m:
            continue
        v = num(r['v1'])
        if v is None:
            continue
        out.setdefault(m.group(1), {})[int(r['fy'])] = v
    return out


def gaps():
    """The registered gaps that bear on these pages, by keyword."""
    out = []
    for r in csv.DictReader(io.open(GAPS, encoding='utf-8')):
        if re.search(r'special.revenue|fund 13|revolving|trust|FY2025 special', (r.get('what') or '') + ' ' + (r.get('why') or ''), re.I):
            out.append({k: r[k] for k in ('side', 'what', 'why') if k in r})
    return out


# --- assemble ------------------------------------------------------------------------------

def build():
    valid, _ = owner_table()
    reg = read_registry()
    depts, revenue, ent = ledger()
    sr, sr_asof = special()
    tr, tr_asof = trusts()
    read_hist, ocr_bal, tr_bal = sr_read_history(), sr_ocr_balances(), trust_ocr_balances()

    measures = {}
    for r in reg:
        m = {k: r[k] for k in r}
        cur, hist, notes = None, [], []
        if r['kind'] in ('appropriation', 'debt'):
            snaps = depts.get(r['code'], {})
            if snaps:
                latest = snaps[max(snaps)]
                cur = dict(latest, grade='evidence')
                m['snapshots'] = [snaps[p] for p in sorted(snaps)]
        elif r['kind'] == 'revenue':
            if r['code'] in revenue:
                cur = dict(revenue[r['code']], grade='evidence')
        elif r['kind'] == 'enterprise':
            if r['code'] in ent:
                cur = dict(ent[r['code']], grade='evidence')
        elif r['kind'] == 'special-revenue':
            if r['code'] in sr:
                cur = dict(sr[r['code']], grade='evidence')
            if r['trend_label']:
                if r['trend_label'] not in read_hist:
                    fail('%s: trend_label %r matches no fund in special-revenue-read.csv' % (r['id'], r['trend_label']))
                hist = sorted(read_hist[r['trend_label']], key=lambda y: y['fy'])
            for fy, v in sorted(ocr_bal.get(r['code'], {}).items()):
                h = dict(fy=fy, closing=r2(v), grade='transcribed',
                         report='sources/data/special-revenue-funds.csv')
                if fy == 2025 and cur:
                    h['chains'] = abs(v - cur['opening']) <= 0.02
                hist.append(h)
        elif r['kind'] in ('trust', 'stabilization', 'agency'):
            if r['code'] in tr:
                cur = dict(tr[r['code']], grade='evidence')
            for fy, v in sorted(tr_bal.get(r['code'], {}).items()):
                h = dict(fy=fy, closing=r2(v), grade='transcribed', report='sources/data/report-trust-funds.csv')
                if fy == 2025 and cur:
                    h['chains'] = abs(v - cur['opening']) <= 0.02
                hist.append(h)
        elif r['kind'] == 'capital':
            for fy, v in sorted(tr_bal.get(r['code'], {}).items()):
                hist.append(dict(fy=fy, closing=r2(v), grade='transcribed', report='sources/data/report-trust-funds.csv'))
            if hist:
                cur = dict(fy=hist[-1]['fy'], closing=hist[-1]['closing'], grade='transcribed', report=hist[-1]['report'])
        if cur is None:
            notes.append('no figure for this measure in any report we hold')
        m['current'] = cur
        m['history'] = hist
        m['notes'] = notes
        measures[r['id']] = m

    # Who owns what, and the roll-ups a page leads with.
    owners = {}
    for m in measures.values():
        for slug, role in ((m['owner'], 'owns'), (m['relates_to'], 'relates')):
            if not slug or slug == 'unresolved':
                continue
            o = owners.setdefault(slug, dict(slug=slug, name=valid[slug][1], kind=valid[slug][0], owns=[], relates=[]))
            o[role].append(m['id'])
    for o in owners.values():
        own = [measures[i] for i in o['owns']]
        o['counts'] = {}
        for m in own:
            o['counts'][m['kind']] = o['counts'].get(m['kind'], 0) + 1
        appro = [m for m in own if m['kind'] in ('appropriation', 'debt') and m['current']]
        srs = [m for m in own if m['kind'] == 'special-revenue' and m['current']]
        trs = [m for m in own if m['kind'] in ('trust', 'stabilization') and m['current']]
        ags = [m for m in own if m['kind'] == 'agency' and m['current']]
        revs = [m for m in own if m['kind'] == 'revenue' and m['current']]
        o['totals'] = dict(
            appropriation_revised=r2(sum(m['current']['revised'] or 0 for m in appro)) if appro else None,
            appropriation_expended=r2(sum(m['current']['expended'] or 0 for m in appro)) if appro else None,
            appropriation_period=max((m['current']['period'] for m in appro), default=None),
            special_revenue_held=r2(sum(m['current']['closing'] for m in srs)) if srs else None,
            special_revenue_in=r2(sum(m['current']['revenue'] for m in srs)) if srs else None,
            special_revenue_out=r2(sum(m['current']['spent'] for m in srs)) if srs else None,
            trust_held=r2(sum(m['current']['closing'] for m in trs)) if trs else None,
            agency_held=r2(sum(m['current']['closing'] for m in ags)) if ags else None,
            revenue_estimate=r2(sum(m['current']['estimate'] for m in revs)) if revs else None,
        )
        o['owns'].sort(key=lambda i: (KIND_ORDER.index(measures[i]['kind']), measures[i]['code']))
        o['relates'].sort()

    unresolved = sorted(i for i, m in measures.items() if m['owner'] == 'unresolved')
    sc = emit('schoolfinance', school_conclusions(measures, sr_asof))
    departments = [r for r in csv.DictReader(io.open(DEPTS, encoding='utf-8'))]

    return dict(
        generated_by='scripts/build_finance.py',
        about='The School Committee’s finances, every line: the appropriation, its revolving funds, grants, gifts and trusts, with what each held at 31 March 2026 and what it has done since FY2011 — the first of a page per board and department, from a registry of every accounting measure the town prints.',
        grain='DOLLARS as the accounting system printed them for FY2026 (evidence), beside the annual reports’ schedules for earlier years (read and tied, or transcribed) — kept apart. An appropriation is a net line, not a cost (rule 11).',
        as_of=dict(ledger='FY2026, period 12 (year end, unaudited) where an account-level report exists; period 9 (31 March 2026) otherwise',
                   special_revenue=sr_asof, trusts=tr_asof),
        kinds=KINDS,
        measures=measures,
        owners=owners,
        departments=departments,
        unresolved=unresolved,
        gaps=gaps(),
        # The routed report is the School Committee's page, so its conclusions are the
        # payload's top-level list (what the master report reads); by-owner is for the rest.
        conclusions=sc,
        conclusions_by_owner={'school-committee': sc},
    )


KIND_ORDER = ['appropriation', 'revenue', 'special-revenue', 'enterprise', 'trust',
              'stabilization', 'agency', 'capital', 'debt']
KINDS = {
    'appropriation': 'a general-fund line Town Meeting votes',
    'revenue': 'a general-fund revenue estimate',
    'special-revenue': 'a revolving, gift, grant or receipts-reserved fund',
    'enterprise': 'an enterprise fund, or the betterments that feed one',
    'trust': 'a trust fund',
    'stabilization': 'a stabilization fund',
    'agency': 'money held for somebody else',
    'capital': 'a capital project fund',
    'debt': 'debt service',
}


SHORT_NAMES = {'1308': 'school choice', '2200': 'school lunch', '1312': 'extended day', '1301': 'athletics', '1306': 'facilities use'}


def school_conclusions(measures, asof):
    own = [m for m in measures.values() if m['owner'] == 'school-committee']
    srs = [m for m in own if m['kind'] == 'special-revenue' and m['current']]
    revolving = [m for m in srs if m['subkind'] == 'revolving']
    grants = [m for m in srs if m['subkind'] == 'grant']
    held = sum(m['current']['closing'] for m in srs)
    rev_held = sum(m['current']['closing'] for m in revolving)
    rev_in = sum(m['current']['revenue'] for m in revolving)
    rev_out = sum(m['current']['spent'] for m in revolving)
    appro = measures['gf-300']['current']
    choice = measures['sr-1308']['current']
    lunch = measures['sr-2200']['current']
    cb = measures['sr-2640']['current']
    deficit = [m for m in grants if m['current']['closing'] < -0.005]
    deficit_total = -sum(m['current']['closing'] for m in deficit)
    biggest = max(revolving, key=lambda m: m['current']['closing'])
    shown = sorted(deficit, key=lambda m: m['current']['closing'])[:6]
    salaried = sorted([m for m in revolving if m['current']['salaries'] > 0], key=lambda m: -m['current']['salaries'])

    share = 100 * held / appro['revised']
    asof_text = '31 March 2026'
    short_asof = 'end of March'
    return [
        conclusion(
            id='outside-the-appropriation',
            claim='The schools hold %s in %s funds outside the appropriation, as of %s.'
                  % (C.usd(held), C.num(len(srs)), short_asof),
            so_what='%s of the %s appropriation, in money Town Meeting never votes on: revolving funds, grants, gifts.' % (C.pct(share, 1), C.usd(appro['revised'])),
            figures={'appropriation': figure(appro['revised'], C.usd(appro['revised']), 'the FY2026 school appropriation, as revised'),
                     'held': figure(held, C.usd(held), 'held in school special-revenue funds at 31 March 2026'),
                     'n': figure(len(srs), C.num(len(srs))), 'share': figure(share, C.pct(share, 1))},
            figure='held', kind='measured', bearing='sizes',
            detail='The town’s FY26 special-revenue report lists every fund with a department code; %s of them carry the schools’ code, 300. Their closing balances sum to %s. '
                   'The general-fund appropriation is department 300 on the FY26 year-end budget report (%s revised, period 12, summed from its accounts). A balance is not a spendable surplus: '
                   'a grant fund’s balance is claimed against a grant’s budget, and a revolving fund’s against the programme that raised it.' % (C.num(len(srs)), C.usd(held), C.usd(appro['revised'])),
            basis='sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx, every row with department code 300, column FUND BALANCE; the expense report’s department 300 total.',
            not_shown='What any balance is committed to. The report is balances, not obligations; the district’s own fund-by-fund plan would say what is spoken for.',
            allow=('300', 'FY26', '2026', '12'),
        ),
        conclusion(
            id='the-revolving-funds',
            claim='The %s school revolving funds took in %s and spent %s in nine months of FY2026.'
                  % (C.num(len(revolving)), C.usd(rev_in), C.usd(rev_out)),
            so_what='They hold %s. Lunch is the largest flow, %s in; %s holds the most, %s.' % (C.usd(rev_held), C.usd(lunch['revenue']), SHORT_NAMES.get(biggest['code'], biggest['name'].title()), C.usd(biggest['current']['closing'])),
            figures={'n': figure(len(revolving), C.num(len(revolving))), 'in': figure(rev_in, C.usd(rev_in), 'into the school revolving funds, FY2026 through March'),
                     'out': figure(rev_out, C.usd(rev_out)), 'held': figure(rev_held, C.usd(rev_held)),
                     'lunch_in': figure(lunch['revenue'], C.usd(lunch['revenue'])), 'biggest': figure(biggest['current']['closing'], C.usd(biggest['current']['closing'])),
                     'choice_in': figure(choice['revenue'], C.usd(choice['revenue'])), 'choice_held': figure(choice['closing'], C.usd(choice['closing'])),
                     'salaried_n': figure(len(salaried), C.num(len(salaried))),
                     **{'sal_%s' % m['code']: figure(m['current']['salaries'], C.usd(m['current']['salaries'])) for m in salaried}},
            figure='in', kind='measured', bearing='sizes',
            detail='A revolving fund is fee or sale income the district may spend without an appropriation, on the programme that raised it: lunch sales, extended day, facilities rental, athletics, '
                   'school choice tuition. Nine months of FY2026: %s in, %s out. School choice took in %s and held %s. %s of the nine pay salaries directly from the fund: %s.'
                   % (C.usd(rev_in), C.usd(rev_out), C.usd(choice['revenue']), C.usd(choice['closing']), C.num(len(salaried)),
                      '; '.join('%s %s' % (SHORT_NAMES.get(m['code'], m['name'].title()), C.usd(m['current']['salaries'])) for m in salaried)),
            basis='The same report, the rows for the revolving funds under department 300 (subkind `revolving` in sources/data/fund-owners.csv); revenue, salaries, expenditure and fund balance, credits shown as amounts.',
            not_shown='What each fund is committed to for the last quarter, or what the year-end balances were: the report stops at 31 March.',
            allow=('300', '2026', 'FY2026'),
        ),
        conclusion(
            id='grants-in-deficit',
            claim='%s of the %s school grant funds were overdrawn at %s, by %s together.'
                  % (C.num(len(deficit)), C.num(len(grants)), asof_text, C.usd(deficit_total)),
            so_what='Spent ahead of the reimbursement — the normal shape of a grant, and town cash until it lands.',
            figures={'deficit_n': figure(len(deficit), C.num(len(deficit))), 'grants_n': figure(len(grants), C.num(len(grants))),
                     'deficit': figure(deficit_total, C.usd(deficit_total), 'overdrawn across the school grant funds at 31 March 2026'),
                     'cb_held': figure(cb['closing'], C.usd(cb['closing'])),
                     **{'d_%s' % m['code']: figure(-m['current']['closing'], C.usd(-m['current']['closing'])) for m in shown}},
            figure='deficit', kind='measured', bearing='sizes',
            detail='The circuit breaker fund (2640) held %s. The overdrawn funds are the reimbursement grants — Title I, IDEA #240, Title II and IV — whose money arrives after the spending it repays. '
                   'The largest: %s.' % (C.usd(cb['closing']), '; '.join('%s %s' % (m['name'].strip(), C.usd(-m['current']['closing'])) for m in shown)),
            basis='The same report, every grant fund (code 25xx–29xx) under department 300, column FUND BALANCE below zero.',
            not_shown='When each reimbursement arrived after 31 March, or whether any grant closed short. The FY26 year-end report would say.',
            allow=('2640', '300', '25', '29', 'FY26', '2026', '31', 'IDEA #240', 'Title I', 'Title II', 'Title IV') + tuple(m['name'].strip() for m in shown),
        ),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    text = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        if have != text:
            fail('%s is stale; run without --check' % os.path.relpath(OUT, ROOT))
        print('finance.json reproduces: %d measures, %d owners, %d unresolved' % (len(data['measures']), len(data['owners']), len(data['unresolved'])))
        return
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(text)
    print('wrote %s: %d measures, %d owners, %d unresolved, %d without a figure' % (
        os.path.relpath(OUT, ROOT), len(data['measures']), len(data['owners']), len(data['unresolved']),
        sum(1 for m in data['measures'].values() if m['current'] is None)))


if __name__ == '__main__':
    main()
