"""Recompute every figure in sources/analyses/athletics-ledger.md from the sources.

Rule 9: a finished document gets re-checked against the data by script, not re-read. Rule 13
adds the sharper version of it — `verify_athletics.py` once passed on a false claim because it
checked that a sentence was present rather than that the sentence's number was right. So every
check here **derives the value first** and only then asks whether the document says it. A
figure that drifts during editing fails; a figure the model stopped producing fails; a sentence
rewritten around a number that is still correct passes, which is the behaviour we want.

Cell-level quotes are checked the same way: the script reads the cell and asserts the document
quotes what the cell actually holds.

    python3 scripts/verify_records_request_2026_06.py

Exit status is the number of failures.
"""
import csv
import os
import re
import sys
import zipfile
from collections import defaultdict

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, 'sources', 'analyses', 'athletics-ledger.md')
REQ = os.path.join(ROOT, 'sources', 'town-ledgers', 'account-details')
JOURNAL = os.path.join(ROOT, 'sources', 'data', 'fund-1301-cash-journal.csv')
BYSPORT = os.path.join(ROOT, 'sources', 'data', 'athletics-by-sport.csv')
RECON = os.path.join(ROOT, 'sources', 'data', 'athletics-by-sport-reconciliation.csv')
HIST = os.path.join(ROOT, 'sources', 'data', 'athletics-history.csv')
FUNDS = os.path.join(ROOT, 'sources', 'budget-workbooks', 'school-funds-fy26.xlsx')

FAILS = []
CHECKS = 0


def load_doc():
    with open(DOC) as fh:
        # The document uses a typographic minus in tables; normalise so a computed
        # '-103,852.53' can be looked for as one string.
        # The document uses a typographic minus and writes money with a dollar
        # sign; normalise both so a computed '-103,852.53' is one string to look for.
        return fh.read().replace('−', '-').replace('$', '')


TEXT = load_doc()


def says(label, value, fmt=',.2f'):
    """Derive first, then require the document to state it."""
    global CHECKS
    CHECKS += 1
    if isinstance(value, str):
        # TEXT has dollar signs stripped so numbers compare as one string; strip them
        # from the expected form too, or a quotation containing '$' can never match.
        forms = [value, value.replace('$', '')]
    else:
        forms = [format(value, fmt)]
        # A whole-dollar figure may legitimately be written without the cents.
        if fmt == ',.2f' and float(value) == int(value):
            forms.append(format(value, ',.0f'))
    s = forms[0]
    if any(f in TEXT for f in forms):
        print(f'  ok    {label:<58} {s}')
    else:
        print(f'  FAIL  {label:<58} {s}  <- not in the document')
        FAILS.append(label)


def head(t):
    print(f'\n{t}\n' + '-' * len(t))


# --- the journal ---------------------------------------------------------------------
rows = list(csv.DictReader(open(JOURNAL)))
for r in rows:
    r['amount'] = float(r['amount'])
    r['fy'] = int(r['fy'])


def fy(y, pred=lambda r: True):
    return [r for r in rows if r['fy'] == y and pred(r)]


head('1. The fund\'s cash, three years')
prior = None
for y in (2024, 2025, 2026):
    soy = [r for r in fy(y) if r['src'] == 'SOY'][0]['amount']
    txn = [r for r in fy(y) if r['src'] != 'SOY']
    rec = sum(r['amount'] for r in txn if r['amount'] > 0)
    pay = sum(r['amount'] for r in txn if r['amount'] < 0)
    close = soy + rec + pay
    says(f'FY{y} opening', soy)
    says(f'FY{y} receipts', rec)
    says(f'FY{y} payments', pay)
    says(f'FY{y} net', rec + pay)
    says(f'FY{y} closing', close)
    if prior is not None:
        assert round(prior, 2) == round(soy, 2), f'FY{y} SOY chain broken'
    prior = close

def as_written(iso):
    y, m, d = iso.split('-')
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
              'August', 'September', 'October', 'November', 'December']
    return f'{int(d)} {months[int(m) - 1]} {y}'


last_eff = max(r['eff_date'] for r in fy(2026) if r['eff_date'])
says('FY2026 last effective date', as_written(last_eff))

# "about five weeks of spending in hand" -- assert the ratio, not the phrase
close24 = ([r for r in fy(2025) if r['src'] == 'SOY'][0]['amount'])
pay24 = -sum(r['amount'] for r in fy(2024) if r['src'] != 'SOY' and r['amount'] < 0)
weeks = close24 / (pay24 / 52)
CHECKS += 1
if 5.0 <= weeks < 6.0:
    label = "FY2024 closing cash as weeks of that year's payments"
    print(f'  ok    {label:<58} {weeks:.2f}')
else:
    print(f'  FAIL  closing cash is {weeks:.2f} weeks of payments, document says "about five"')
    FAILS.append('five weeks')

head('2. The ADJ EXP journal entries')
gen25 = [r for r in fy(2025) if r['src'] == 'GEN']
for r in sorted(gen25, key=lambda r: r['eff_date']):
    says(f"FY25 GEN {r['eff_date']} journal {r['journal']}", r['amount'])
    says(f"  its comment", r['comments'])
    says(f"  its posted date", r['post_date'])
total25 = sum(r['amount'] for r in gen25)
says('FY2025 ADJ EXP total', total25)
gen24 = sum(r['amount'] for r in fy(2024) if r['src'] == 'GEN')
says('FY2024 ADJ EXP total', gen24)
says('FY2024 ADJ EXP comment', [r for r in fy(2024) if r['src'] == 'GEN'][0]['comments'])
close25 = ([r for r in fy(2026) if r['src'] == 'SOY'][0]['amount'])
says('FY2025 closing cash without the four entries', close25 - total25)
says('two-year ADJ EXP total', total25 + gen24)
CHECKS += 1
share = total25 / sum(r['amount'] for r in fy(2025) if r['src'] != 'SOY' and r['amount'] > 0)
if f'{share:.0%}' in TEXT:
    print(f"  ok    {'ADJ EXP share of FY2025 receipts':<58} {share:.0%}")
else:
    print(f'  FAIL  ADJ EXP share of FY2025 receipts is {share:.0%}')
    FAILS.append('ADJ EXP share')
CHECKS += 1
if [r for r in fy(2026) if r['src'] == 'GEN']:
    print('  FAIL  FY2026 has GEN entries; the document says it has none')
    FAILS.append('FY2026 GEN')
else:
    print(f"  ok    {'FY2026 has no GEN entries':<58} 0")

head('3. Where the money goes, by source code')
for y in (2024, 2025, 2026):
    for src in ('CRP', 'APP', 'PRJ', 'GRV'):
        says(f'FY{y} {src}', sum(r['amount'] for r in fy(y) if r['src'] == src))

wb = openpyxl.load_workbook(FUNDS, data_only=True)
b19 = wb['Athletics Revolving']['B19'].value
prj26 = sum(r['amount'] for r in fy(2026) if r['src'] == 'PRJ')
CHECKS += 1
if round(-prj26, 2) == round(b19, 2):
    print(f"  ok    {'FY2026 payroll equals school-funds-fy26!B19':<58} {b19:,.2f}")
else:
    print(f'  FAIL  FY2026 payroll {-prj26:,.2f} != school-funds-fy26!B19 {b19:,.2f}')
    FAILS.append('payroll tie')
says('the salary line label quoted from B19',
     str(wb['Athletics Revolving']['A19'].value))

for y, ref in ((2024, 'REVFEE'), (2025, 'REVFEE'), (2026, 'REVFEE')):
    v = sum(r['amount'] for r in fy(y)
            if r['src'] == 'CRP' and ref in (r['ref3'] or r['reference'] or '').upper())
    says(f'FY{y} processor fees', v)

head('4. Reconciling to the fund\'s own FY26 report')
c5 = wb['Athletics Revolving']['C5'].value
says('beginning undesignated fund balance at 1 July 2025', c5)
soy26 = [r for r in fy(2026) if r['src'] == 'SOY'][0]['amount']
says('opening cash at 1 July 2025', soy26)
says('the difference', soy26 - c5)
# The first FY2026 movement is a $250 receipt; the document is about the first
# disbursement, which is the next row.
first26 = sorted([r for r in fy(2026) if r['src'] != 'SOY' and r['amount'] < 0],
                 key=lambda r: (r['eff_date'], r['journal']))[0]
says('first FY2026 disbursement', first26['amount'])
says('  its effective date', as_written(first26['eff_date']))
says('  its warrant reference', first26['reference'])
says('ending balance the report prints', wb['Athletics Revolving']['C8'].value)
CHECKS += 1
# A16 is on the Summary sheet, not the Athletics Revolving sheet -- checked here
# because the document cites it by sheet and cell.
a16 = str(wb['Summary']['A16'].value)
quoted = '~$20,991.20 of FY26 spending was recorded as Accounts Payable at 6/30/26'
if quoted in a16 and quoted.replace('$', '') in TEXT:
    print(f"  ok    {'A16 quoted verbatim':<58} present in both")
else:
    print('  FAIL  the A16 quotation does not match the cell')
    FAILS.append('A16 quote')
m = re.search(r'Cash increased only \$([\d,]+\.\d\d)', str(wb['Athletics Revolving']['A26'].value))
says('cash increase the report states', m.group(1))

head('5. Athletics all-in, from the sport workbook')
sw = openpyxl.load_workbook(
    os.path.join(REQ, 'athletics-by-sport-fy2024-fy2026.xlsx'), data_only=True)
SEASON_TOTALS = {
    2024: [('Fall', 'BM26', 'BM28'), ('Winter', 'BN23', 'BN26'), ('Spring', 'BN25', 'BN28')],
    2025: [('Fall', 'BN26', 'BN28'), ('Winter', 'BO23', 'BO26'), ('Spring', 'BO25', 'BO28')],
}
sport = list(csv.DictReader(open(BYSPORT)))


def col(fyr, metric, season=None, level=None):
    t = 0.0
    for r in sport:
        if int(r['fy']) != fyr or r['metric'] != metric:
            continue
        if season and r['season'] != season:
            continue
        if level and r['level'] != level:
            continue
        if r['value'] not in ('', 'None', None):
            t += float(r['value'])
    return t


# Where each sheet prints its share of the costs common to all three seasons.
SHARED = {(2024, 'Fall'): 'AX26', (2024, 'Winter'): 'AY23', (2024, 'Spring'): 'AY25',
          (2025, 'Fall'): 'AY26', (2025, 'Winter'): 'AZ23', (2025, 'Spring'): 'AZ25'}

for y in (2024, 2025):
    inc = []
    for season, c_ex, _ in SEASON_TOTALS[y]:
        printed = sw[season][c_ex].value
        # Spring FY2025's printed total is demonstrably short; the document says so and
        # uses the row sum instead. Reproduce that choice here rather than assume it.
        rowsum = col(y, 'Total Expenses', season=season)
        use = rowsum if abs((printed or 0) - rowsum) > 0.005 else printed
        says(f'FY{y} {season} season total', use)
        inc.append(use + sw[season][SHARED[(y, season)]].value)
    says(f'FY{y} all-in', sum(inc))

says('Spring FY2025 printed total', sw['Spring']['BO25'].value)
says('Spring FY2025 rows sum', col(2025, 'Total Expenses', season='Spring'))

recon = list(csv.DictReader(open(RECON)))
ties = sum(int(r['ties']) for r in recon)
says('reconciliation checks', str(len(recon)))
says('  of which tie', str(ties))
says('  of which do not', str(len(recon) - ties))

head('6. Transportation')
for y in (2024, 2025):
    for season in ('Fall', 'Winter', 'Spring'):
        says(f'FY{y} {season} transportation', col(y, 'Transportation', season=season))
    says(f'FY{y} transportation total', col(y, 'Transportation'))

hist = list(csv.DictReader(open(HIST)))
gf = defaultdict(float)
for r in hist:
    if r['side'] == 'general':
        gf[(int(r['fy']), r['item'])] += float(r['amount'])
for y in (2024, 2025):
    line = gf[(y, 'Athletic Transportation')]
    says(f'FY{y} general fund transportation line', line)
    says(f'FY{y} residual', col(y, 'Transportation') - line)

head('7. General fund comparison, FY2024')
MAP = {
    'Official': ['Athletic Officials'],
    'Coaches': ['Athletic Coaches', 'Freshman & MS Coaches', 'Unified Sports Coach'],
    'Transportation': ['Athletic Transportation'],
    'Uniforms': ['Athletic Replacement of Uniforms'],
}
OTHER = ['Assignor', 'Police/ EMS', 'Equipment Recon', 'Dues & Fees', 'Equipment', 'Misc']
OTHER_GF = ['Special Detail/Athletic Events', 'Athletic Equipment/Reconditioning',
            'Athletic Dues & Fees', 'Athletic New Equipment']
tw = tg = 0.0
for k, lines in MAP.items():
    w = col(2024, k)
    g = sum(gf[(2024, l)] for l in lines)
    says(f'FY2024 {k} workbook', w)
    says(f'FY2024 {k} general fund', g)
    says(f'FY2024 {k} outside', w - g)
    tw += w
    tg += g
ow = sum(col(2024, k) for k in OTHER)
og = sum(gf[(2024, l)] for l in OTHER_GF)
says('FY2024 everything else matched, workbook', ow)
says('FY2024 everything else matched, general fund', og)
says('FY2024 everything else, outside', ow - og)
says('FY2024 workbook total', tw + ow)
says('FY2024 comparable general fund total', tg + og)
says('FY2024 outside the general fund', (tw + ow) - (tg + og))
unmatched = sum(gf[(2024, i)] for i in
                ['Athletic Director', 'Athletic Trainer', 'Athletic Insurance'])
says('FY2024 general fund lines with no workbook counterpart', unmatched)
CHECKS += 1
pct = (tg + og) / (tw + ow)
if f'{pct:.0%}' in TEXT:
    print(f"  ok    {'appropriation as a share of workbook cost':<58} {pct:.0%}")
else:
    print(f'  FAIL  appropriation covers {pct:.0%} of workbook cost')
    FAILS.append('44 percent')

head('8. The fee schedule')
# The document quotes these by coordinate. Assert the coordinate holds what it quotes.
for cell in ('E3', 'F3', 'G3'):
    says(f'Spring!{cell} quoted with its value',
         f"Spring!{cell} = {sw['Spring'][cell].value}")
says('Spring!E1 quoted', f"`Spring!E1 = '{sw['Spring']['E1'].value}'`")
for c in ('E2', 'F2', 'G2'):
    says(f'Spring!{c} quoted', f"{c}='{sw['Spring'][c].value}'")
for cell in ('Q3', 'R3', 'S3', 'T3', 'U3', 'V3'):
    says(f'Spring!{cell} quoted', f"`{cell}={sw['Spring'][cell].value}`")
for sheet, cell in (('Fall', 'A21'), ('Winter', 'A18'), ('Spring', 'A20')):
    says(f'{sheet}!{cell} coordinate', f"`{sheet}!{cell}`")
    says(f'{sheet}!{cell} value', f"`'{sw[sheet][cell].value}'`")
for cell in ('J3', 'M3'):
    CHECKS += 1
    if sw['Spring'][cell].value is None and f'`Spring!{cell}`' in TEXT:
        print(f"  ok    {'Spring!' + cell + ' is empty, as stated':<58} empty")
    else:
        print(f'  FAIL  Spring!{cell} = {sw["Spring"][cell].value!r}')
        FAILS.append(f'Spring!{cell}')

hs_gross = wb['Athletics Revolving']['B12'].value
ms_gross = wb['Athletics Revolving']['B13'].value
hs_n = col(2026, 'Total Athletes', level='HS')
ms_n = col(2026, 'Total Athletes', level='MS')
says('FY26 high school gross fees', hs_gross)
says('FY26 middle school gross fees', ms_gross)
says('FY26 high school participations', f'{hs_n:.0f}')
says('FY26 middle school participations', f'{ms_n:.0f}')
says('FY26 high school per participation', hs_gross / hs_n)
says('FY26 middle school per participation', ms_gross / ms_n)
says('workbook FY26 participations', f'{hs_n + ms_n:.0f}')

head('9. The fee-count document')
xml = zipfile.ZipFile(os.path.join(REQ, 'athletic-fee-counts-fy2026.docx')
                      ).read('word/document.xml').decode('utf8')
lines = [re.sub(r'<[^>]+>', '', p).strip()
         for p in re.sub(r'</w:p>', '\n', xml).split('\n')]
lines = [l for l in lines if l]
counts, season = defaultdict(list), None
for l in lines:
    if l.lower() in ('fall', 'winter', 'spring'):
        season = l.lower()
        continue
    m = re.match(r'^(.*?)\s+(\d+)$', l)
    if m and season:
        counts[season].append((m.group(1).strip(), int(m.group(2))))
says('docx title', lines[0])
for s in ('fall', 'winter', 'spring'):
    for label, n in counts[s]:
        if 'cap' in label.lower():
            continue
        says(f'docx {s} {label}', str(n))
tot = sum(n for s in counts for label, n in counts[s] if 'cap' not in label.lower())
says('docx participations total', str(tot))
waivers = sum(n for s in counts for label, n in counts[s] if 'waiver' in label.lower())
full = sum(n for s in counts for label, n in counts[s] if label.lower().startswith('full pay'))
says('docx full waivers', str(waivers))
says('docx full pay', str(full))

head('10. The document-basis classification')
basis = {r['path']: r for r in csv.DictReader(
    open(os.path.join(ROOT, 'sources', 'data', 'document-basis.csv')))}
says('documents scanned', str(len(basis)))
ledger = [p_ for p_, r in basis.items() if r['source_type'] == 'ledger']
says('ledger documents', str(len(ledger)))
for y in (24, 25, 26):
    k = f'sources/town-ledgers/account-details/account-details-fy20{y}-fund1301.xlsx'
    CHECKS += 1
    if basis.get(k, {}).get('source_type') == 'ledger':
        print(f"  ok    {'FY' + str(y) + ' journal classified ledger':<58} ledger")
    else:
        print(f'  FAIL  {k} is {basis.get(k, {}).get("source_type")!r}, not ledger')
        FAILS.append(f'basis fy{y}')
k = 'sources/town-ledgers/account-details/athletics-by-sport-fy2024-fy2026.xlsx'
CHECKS += 1
if basis.get(k, {}).get('source_type') == 'narrative':
    print(f"  ok    {'sport workbook classified narrative, as disclosed':<58} narrative")
else:
    print(f'  FAIL  sport workbook is {basis.get(k, {}).get("source_type")!r}; '
          'the document says narrative')
    FAILS.append('basis workbook')


head("11. The requester's name appears nowhere we wrote")
# TJ asked on 29 August 2026 that the requester not be named. Enforcing that with a
# hardcoded name would put the name in the repository, which is the thing being avoided --
# so it is read from the original request form, which lives only in the gitignored staging
# directory and is never published. If that file is absent (a fresh clone, another machine)
# the check says it could not run rather than passing quietly.
#
# Scope is deliberately OUR OWN WRITING, not the whole archive. The town publishes meeting
# minutes and tax-taking notices that name residents, and this project mirrors those
# verbatim; editing them would mean the archive no longer holds the document the town
# published, which is a worse problem than the one being solved. The rule is that WE do not
# name him, not that his name is scrubbed from the town's records.
import glob
forms = glob.glob(os.path.join(ROOT, 'incoming', '*', 'Public Records Request Form.pdf'))
CHECKS += 1
if not forms:
    print('  skip  original request form not present locally — cannot verify absence')
else:
    from pypdf import PdfReader
    fields = PdfReader(forms[0]).get_fields() or {}
    who = str((fields.get('Name of Requestor') or {}).get('/V') or '').strip()
    surname = [w for w in re.split(r'\s+', who) if len(w) > 2][-1:] or [who]
    OURS = [os.path.join(ROOT, 'sources', 'analyses'),
            os.path.join(ROOT, 'sources', 'town-ledgers', 'account-details'),
            os.path.join(ROOT, 'sources', 'data'),
            os.path.join(ROOT, 'notes'),
            os.path.join(ROOT, 'scripts'),
            os.path.join(ROOT, 'fy28', 'src'),
            os.path.join(ROOT, 'fy28', 'public', 'docs', 'analyses'),
            os.path.join(ROOT, 'fy28', 'public', 'docs', 'town-ledgers', 'account-details'),
            os.path.join(ROOT, 'fy28', 'public', 'docs', 'data')]
    scanned = leaked = 0
    for base in OURS:
        for dirpath, _dirnames, filenames in os.walk(base):
            for fn in filenames:
                if not fn.endswith(('.md', '.csv', '.txt', '.json', '.py', '.ts', '.tsx', '.mjs')):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    body = open(fp, encoding='utf-8', errors='ignore').read().lower()
                except OSError:
                    continue
                scanned += 1
                if any(part.lower() in body for part in surname) or who.lower() in body:
                    print(f'  FAIL  requester named in {os.path.relpath(fp, ROOT)}')
                    leaked += 1
    if leaked:
        FAILS.append('requester named')
    else:
        print(f'  ok    {"name absent from " + str(scanned) + " files we wrote":<58} '
              "the town's own records are mirrored verbatim and not scanned")


head('12. Provenance')
prov = open(os.path.join(REQ, 'PROVENANCE-fund1301.md')).read()
import hashlib
for f in sorted(os.listdir(REQ)):
    # The provenance note cannot record its own sha256. It was called `PROVENANCE.md` when
    # this was written and the archive reorg renamed it; the skip did not follow, so the
    # check demanded that a file contain the hash of itself.
    if f.startswith('PROVENANCE'):
        continue
    h = hashlib.sha256(open(os.path.join(REQ, f), 'rb').read()).hexdigest()
    CHECKS += 1
    if h in prov:
        print(f'  ok    {f:<58} {h[:16]}…')
    else:
        print(f'  FAIL  {f} sha256 not recorded in PROVENANCE.md')
        FAILS.append(f'sha {f}')

print(f'\n{CHECKS} checks, {len(FAILS)} failed')
for f in FAILS:
    print(f'  - {f}')
sys.exit(len(FAILS))
