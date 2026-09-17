"""The account registry: every accounting measure the town's reports print, and who owns it.

    python3 scripts/build_fund_owners.py --seed    # add any measure a held report prints that
                                                   #   the registry lacks, owner from the rules
                                                   #   below (basis recorded) or `unresolved`
    python3 scripts/build_fund_owners.py --check   # fail if a held report prints a measure the
                                                   #   registry does not list, or an owner is not
                                                   #   a board, a department, or `unresolved`

TJ, 17 September 2026: "realistically, we need to take every fund and account we know of,
break it down into which 'department' owns them, and build those relevant pages, leaving
none out from being listed somewhere ... make sure you aren't over indexing on my word
'fund'. I mean, all accounting measures should be trackable, and trendable."

So the registry is not a list of funds. It is one row per thing the accounting system
carries a balance or a budget for, in whichever report it prints it:

    appropriation     a general-fund department line, as Town Meeting votes it
                      (the accounts inside a department inherit its owner)
    revenue           a general-fund revenue estimate, one row per MUNIS revenue account
    special-revenue   a revolving, gift, grant or receipts-reserved fund
    enterprise        an enterprise fund, or a betterment fund that feeds one
    trust             a trust fund, expendable or not
    stabilization     a stabilization fund
    agency            an agency account (money held for somebody else)
    capital           a capital project fund
    debt              a debt-service line

`owner` is the board or department that spends the money or administers the fund, by the
slugs in fy28/public/data/boards.json and sources/data/departments.csv. `owner_basis` says
what that rests on -- the town's own org code on the fund-balance report, the department a
line is filed under in the ledger, or the fund's name -- because ownership is our reading
of the town's books, not something the books state (rule 3). `relates_to` is a second
page the row belongs on: Chapter 70 is the Treasurer's receipt and the School Committee's
money.

The file is hand-maintained once seeded: an owner is a judgment, and this script never
overwrites one. What it does enforce is completeness -- a measure that is in a report and
not in the registry fails the build, which is the whole point of having one.
"""
import argparse
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, 'sources', 'data', 'fund-owners.csv')
DEPTS = os.path.join(ROOT, 'sources', 'data', 'departments.csv')
BOARDS = os.path.join(ROOT, 'fy28', 'public', 'data', 'boards.json')
LEDGER = os.path.join(ROOT, 'sources', 'data', 'munis-ledger.csv')
SPECIAL = os.path.join(ROOT, 'sources', 'town-ledgers', 'fund-balances', 'special-revenue-fy2026-p09.xlsx')
TRUST = os.path.join(ROOT, 'sources', 'town-ledgers', 'fund-balances', 'trust-agency-fy2026-p09.xlsx')
TRUST_HISTORY = os.path.join(ROOT, 'sources', 'data', 'report-trust-funds.csv')

FIELDS = ['id', 'kind', 'subkind', 'code', 'name', 'owner', 'owner_basis', 'relates_to',
          'purpose', 'authority', 'trend_label', 'report']
OWNER_KINDS = {'board', 'department', 'external', 'unresolved'}


def fail(msg):
    sys.stderr.write('build_fund_owners: %s\n' % msg)
    sys.exit(1)


def rel(p):
    return os.path.relpath(p, ROOT)


# --- who can own something -----------------------------------------------------------------

def owners():
    """Every slug an `owner` may name, and the MUNIS department codes each one is filed under."""
    out, by_code = {}, {}
    for b in json.load(io.open(BOARDS, encoding='utf-8'))['boards']:
        out[b['slug']] = ('board', b['name'])
    for r in csv.DictReader(io.open(DEPTS, encoding='utf-8')):
        if r['slug'] in out:
            fail('departments.csv slug %r collides with a board' % r['slug'])
        out[r['slug']] = (r['kind'], r['name'])
        for c in filter(None, r['dept_codes'].split(';')):
            by_code[c.strip()] = r['slug']
    # Boards that ARE the department the ledger files a line under. The ledger's own
    # department names are the evidence: 122 is SELECT BOARD, 300 is SCHOOL DEPARTMENT.
    for code, slug in BOARD_CODES.items():
        by_code.setdefault(code, slug)
    for slug in set(by_code.values()):
        if slug not in out:
            fail('department code maps to unknown owner %r' % slug)
    return out, by_code


BOARD_CODES = {
    '122': 'select-board', '131': 'finance-committee', '132': 'finance-committee',
    '141': 'board-of-assessors', '175': 'planning-board', '176': 'zoning-board-of-appeals',
    '178': 'architectural-preservation-district-commission', '171': 'conservation-commission',
    '300': 'school-committee', '301': 'school-committee', '491': 'cemetery-commission',
    '512': 'board-of-health', '521': 'board-of-health', '522': 'board-of-health',
    '541': 'council-on-aging', '610': 'library-board-of-trustees', '650': 'parks-commission',
    '691': 'historical-commission', '693': 'select-board', '134': 'trust-fund-commission',
    '993': 'capital-planning-committee', '996': 'town-meeting',
}

# General-fund revenue accounts, by the MUNIS object code the estimate is booked under.
# Default is the Treasurer/Collector, who receipts everything; these are the accounts a
# department raises itself, and the ones that are the schools' money in all but the ledger.
REVENUE_RULES = [
    (r'^43(01|10)|^4418|^4701|^4714|^4374', 'police', ''),                    # police reports, permits, court and parking fines
    (r'^4302|^4316|^4417|^4716|^4703', 'fire', ''),                            # fire reports, permits, fines, the ambulance
    (r'^4306|^4307|^4308|^4309|^4339|^4340|^4403|^4407', 'town-clerk', ''),     # vitals, certificates, lists, dog and marriage licences
    (r'^4324|^4326|^4327|^4321|^4323|^4325|^4359|^4360|^4368', 'planning-board', ''),
    (r'^4328', 'zoning-board-of-appeals', ''),
    (r'^4329|^4330|^4331|^4717', 'conservation-commission', ''),
    (r'^4333|^4350|^4370', 'cemetery-commission', ''),
    (r'^4315|^441[0-5]|^4423|^4311', 'building-inspection', ''),
    (r'^4404|^4406', 'board-of-health', ''),
    (r'^4401|^4402|^4405|^4408|^4313|^4357|^4367|^4377', 'select-board', ''),   # licences the board grants; leases it signs
    (r'^4318|^4718', 'animal-control', ''),
    (r'^4372|^4362', 'parks-commission', ''),
    (r'^4725|^4383', 'facilities', ''),                                        # net metering, building rental
    (r'^4319|^4376|^4382|^4506|^4511|^4529|^4730|^4507|^4509|^4512|^4513', 'treasurer-collector', 'school-committee'),
    (r'^4363', 'treasurer-collector', 'school-committee'),
    (r'^4502|^4503|^4504|^4505', 'board-of-assessors', ''),                     # abatement reimbursements
]


# --- what the reports print ------------------------------------------------------------------

def ledger_measures(by_code):
    """General-fund departments, revenue accounts, enterprise and betterment funds, debt."""
    rows = list(csv.DictReader(io.open(LEDGER, encoding='utf-8')))
    out = {}
    for r in rows:
        if r['fund'] == '0100' and r['level'] == 'department':
            code = r['dept']
            kind = 'debt' if code in ('710', '751', '754') else 'appropriation'
            sub = ('debt service' if kind == 'debt' else
                   'reserve' if code in ('132', '133') else
                   'assessment' if code in ('310', '820', '825', '841') else
                   'benefits and insurance' if code[0] == '9' and code not in ('993', '996') else
                   'transfer' if code in ('993', '996') else '')
            o = by_code.get(code)
            out['gf-%s' % code] = dict(
                id='gf-%s' % code, kind=kind, subkind=sub, code=code, name=r['name'].strip(),
                owner=o or 'unresolved', relates_to='',
                owner_basis='the department the ledger files it under' if o else '',
                report=r['doc_id'])
        elif r['fund'] == '0100' and r['account_type'] == 'revenue' and r['level'] == 'account':
            obj = r['object']
            o, rel_ = 'treasurer-collector', ''
            basis = 'receipted by the Treasurer/Collector; no department raises it'
            for pat, slug, rel2 in REVENUE_RULES:
                if re.match(pat, obj):
                    o, rel_, basis = slug, rel2, 'the department that raises it, by the account name'
                    break
            out['rev-%s' % obj] = dict(
                id='rev-%s' % obj, kind='revenue',
                subkind=('tax' if obj[:2] == '41' else 'fee or permit' if obj[:2] in ('43', '44') else
                         'state aid' if obj[:2] == '45' else 'federal' if obj[:2] == '46' else
                         'fine or miscellaneous' if obj[:2] == '47' else 'interest and transfers'),
                code=obj, name=r['name'].strip(), owner=o, owner_basis=basis, relates_to=rel_,
                report=r['doc_id'])
        elif r['fund'] != '0100' and r['level'] in ('department', 'account'):
            f = r['fund']
            out.setdefault('ef-%s' % f, dict(
                id='ef-%s' % f, kind='enterprise',
                subkind='betterment' if 'BETTER' in r['fund_name'] else 'enterprise fund',
                code=f, name=r['fund_name'].strip(),
                owner=ENTERPRISE.get(f, 'unresolved'),
                owner_basis='the board that sets its rates' if f in ENTERPRISE else '',
                relates_to='', report=r['doc_id']))
    return out


ENTERPRISE = {'6000': 'sewer-commission', '5000': 'sewer-commission', '6100': 'dpw',
              '5100': 'dpw', '7900': 'dpw', '6200': 'select-board'}


def special_revenue(by_code):
    """Every fund on the FY26 special-revenue report, with the town's own org code."""
    import openpyxl
    ws = openpyxl.load_workbook(SPECIAL, read_only=True, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = {str(v).strip(): i for i, v in enumerate(rows[6]) if v}
    fi, ni = hdr['FUND'], hdr['FUND DESCRIPTION']
    # The department code sits in the column between FUND DESCRIPTION and the one labelled
    # ACCOUNT ORG CODE (which repeats the fund number), and that column carries no label at
    # all. It is a MUNIS department code -- 300 on every school fund, 210 on every police
    # grant, 610 on the library's -- and that is what the owner rests on. Read it by
    # position, and say so in the basis.
    oi = hdr['ACCOUNT ORG CODE'] - 1
    out = {}
    for r in rows[7:]:
        f = r[fi]
        # Two fund codes are stored as text with Excel's apostrophe prefix (2200, 8115).
        if isinstance(f, str) and f.strip("' ").isdigit():
            f = int(f.strip("' "))
        if not isinstance(f, (int, float)):
            continue
        f = str(int(f))
        if f == '8115':
            continue          # a trust fund printed on the wrong report; it is registered from the trust report
        name = str(r[ni] or '').strip("' ").strip()
        org = r[oi]
        org = str(int(org)) if isinstance(org, (int, float)) and org > 0 else ''
        if f in out:
            continue
        sub = ('grant' if f[0] == '2' and f[:2] != '22' else
               'revolving' if 'REVOLV' in name or f == '2200' else
               'gift' if 'GIFT' in name else
               'receipts reserved' if 'RESERVED' in name or 'RECEIPTS' in name else 'other')
        o = by_code.get(org) if org != f else None
        out['sr-%s' % f] = dict(
            id='sr-%s' % f, kind='special-revenue', subkind=sub, code=f, name=name,
            owner=o or 'unresolved', relates_to='',
            owner_basis=('department code %s in the unlabelled column of the town’s special-revenue report' % org) if o else '',
            report=rel(SPECIAL))
    return out


def trusts():
    """Every trust, stabilization and agency account on the FY26 trust report."""
    import openpyxl
    wb = openpyxl.load_workbook(TRUST, read_only=True, data_only=True)
    ws = wb['Sheet2']
    out = {}
    for r in ws.iter_rows(values_only=True):
        v = [x for x in r if x is not None]
        if not v or not isinstance(v[0], (int, float)) or len(v) < 2 or not isinstance(v[1], str):
            continue
        code, name = str(int(v[0])), v[1].strip()
        kind = ('agency' if code[0] == '9' else
                'stabilization' if re.search(r'stabil|opeb|opiod|vehicle equipment|conservation trust|playground fund|sewer cap', name, re.I) and code in STAB else
                'trust')
        o = TRUST_OWNERS.get(code)
        out['tr-%s' % code] = dict(
            id='tr-%s' % code, kind=kind,
            subkind='scholarship' if 'scholar' in name.lower() else '',
            code=code, name=name, owner=o or 'unresolved',
            owner_basis='the fund’s name' if o else '', relates_to='', report=rel(TRUST))
    return out


STAB = {'8124', '8125', '8129', '8133', '8136', '8137', '8138', '8140', '8141'}
TRUST_OWNERS = {
    '8000': 'cemetery-commission', '8001': 'cemetery-commission', '8115': 'cemetery-commission',
    '8127': 'cemetery-commission', '8114': 'library-board-of-trustees',
    '8116': 'school-committee', '8119': 'school-committee', '8121': 'dpw',
    '8124': 'town-meeting', '8125': 'conservation-commission', '8126': 'parks-commission',
    '8132': 'sewer-commission', '8133': 'sewer-commission', '8138': 'sewer-commission',
    '8136': 'capital-planning-committee', '8137': 'treasurer-collector',
    '8140': 'town-manager', '8141': 'board-of-health', '8144': 'town-manager',
    '8111': 'cultural-council', '8131': 'select-board',
    '9000': 'board-of-assessors', '9001': 'police', '9002': 'school-committee',
}


def capital_funds():
    """Capital project funds, from the FY2025 annual report's fund-balance table -- the only
    place the 3xxx funds are printed. Labelled `code name`; the code is the fund."""
    out = {}
    for r in csv.DictReader(io.open(TRUST_HISTORY, encoding='utf-8')):
        if r['fy'] != '2025' or r['kind'] != 'row':
            continue
        m = re.match(r'^\s*(3\d{3})\s+(.*\S)', r['label'] or '')
        if not m:
            continue
        code, name = m.group(1), re.sub(r'\s+', ' ', m.group(2))
        o = CAPITAL_OWNERS.get(code, 'capital-planning-committee' if 'cap' in name.lower() else None)
        out['cp-%s' % code] = dict(
            id='cp-%s' % code, kind='capital', subkind='capital project fund', code=code, name=name,
            owner=o or 'unresolved', owner_basis='the article the fund’s name cites' if o else '',
            relates_to='', report='sources/data/report-trust-funds.csv')
    return out


CAPITAL_OWNERS = {'3006': 'cemetery-commission', '3053': 'sewer-commission', '3100': 'dpw',
                  '3102': 'select-board', '3106': 'select-board', '3108': 'parks-commission',
                  '3110': 'historical-commission', '3114': 'school-committee'}


def printed():
    _, by_code = owners()
    out = {}
    for part in (ledger_measures(by_code), special_revenue(by_code), trusts(), capital_funds()):
        out.update(part)
    return out


# --- the registry ---------------------------------------------------------------------------

def read():
    if not os.path.exists(REG):
        return []
    with io.open(REG, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def write(rows):
    rows = sorted(rows, key=lambda r: (KIND_ORDER.index(r['kind']), r['code']))
    with io.open(REG, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in FIELDS})


KIND_ORDER = ['appropriation', 'revenue', 'special-revenue', 'enterprise', 'trust',
              'stabilization', 'agency', 'capital', 'debt']


def seed():
    have = {r['id']: r for r in read()}
    found = printed()
    added = 0
    for k, row in found.items():
        if k not in have:
            have[k] = dict(row, purpose='', authority='', trend_label='')
            added += 1
    write(list(have.values()))
    print('fund-owners.csv: %d rows, %d added' % (len(have), added))


def check():
    valid, _ = owners()
    reg = read()
    ids = {r['id'] for r in reg}
    problems = []
    for k, row in printed().items():
        if k not in ids:
            problems.append('MISSING  %-8s %-6s %s  (%s)' % (row['kind'], row['code'], row['name'], row['report']))
    for r in reg:
        if r['owner'] != 'unresolved' and r['owner'] not in valid:
            problems.append('OWNER    %s names %r, which is no board or department' % (r['id'], r['owner']))
        if r['relates_to'] and r['relates_to'] not in valid:
            problems.append('RELATES  %s names %r' % (r['id'], r['relates_to']))
        if r['owner'] != 'unresolved' and not r['owner_basis']:
            problems.append('BASIS    %s has an owner and no owner_basis' % r['id'])
        if r['kind'] not in KIND_ORDER:
            problems.append('KIND     %s: %r' % (r['id'], r['kind']))
    if problems:
        fail('%d problem(s)\n  ' % len(problems) + '\n  '.join(problems))
    unresolved = [r for r in reg if r['owner'] == 'unresolved']
    print('fund-owners.csv: %d measures, every one a held report prints; %d unresolved'
          % (len(reg), len(unresolved)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.seed:
        seed()
    if a.check or not a.seed:
        check()


if __name__ == '__main__':
    main()
