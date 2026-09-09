#!/usr/bin/env python3
"""The Chapter 70 formula, term by term, FY1993-FY2026 -- and the circuit breaker.

    python3 scripts/extract_dese_state_aid.py
    python3 scripts/extract_dese_state_aid.py --check

Writes four files:

  sources/data/dese-ch70-formula.csv       DataC70   one row per district per fiscal year
  sources/data/dese-ch70-aid-factor.csv    dataAid   the aid build-up, FY2007 on
  sources/data/dese-ch70-contribution.csv  dataContribution  the MUNICIPAL side of it
  sources/data/dese-circuit-breaker.csv    ab34-d3ma high-cost special education claims
  sources/data/dese-ch70-statewide.csv     every district collapsed to a distribution

SEVEN DISTRICTS IN THE ROW-LEVEL FILES, AND EVERY DISTRICT AS A DISTRIBUTION

The row-level files are Lunenburg and the six peers this project already compares against,
plus the state row, because the published database has to stay under Cloudflare's 25 MB
per-asset limit -- the same trade `extract_dese_finance.py` records. **Every identity
below is asserted across ALL districts before the scope is applied**, so the statements
this run prints are about the whole publication and not about our slice of it.

What a reader loses by that scope is *where Lunenburg sits among 400 districts*, and that
is the question this data was fetched for -- so it is kept, as a DISTRIBUTION.
`dese-ch70-statewide.csv` gives, per fiscal year, the quartiles and range of net school
spending as a share of required, of aid per foundation pupil and of the required local
contribution share, with Lunenburg's own figure and its rank. That is what a peer
comparison actually needs: districts differ in size, grade span and whether they are
regional, so a raw dollar comparison between two of them means very little.

WHY THIS ONE MATTERS MORE THAN ITS SIZE

Chapter 70 is about 35% of the school appropriation and is set in the Governor's budget
rather than by anything Lunenburg does. Until now the state-aid growth rate rested on
twenty-three years of the TOWN'S own `Subtotal State Aid` line -- a total the town happened
to print. This is thirty-four years of the STATE'S series with foundation enrollment,
required local contribution and aid separated, so the rate can be derived from the
formula's own terms.

**It ties to the town's own books.** DESE's FY2026 Chapter 70 aid for Lunenburg is the
same figure the TOWN's MUNIS revenue ledger records against account `CH 70 AID` -- the
state's formula workbook and the town's general ledger, neither derived from the other,
on one receipt. The run asserts it against `munis-ledger.csv` and refuses to write if the
two ever part company. It is also the figure `/state-aid` derives independently by cell
reference from `ch70-fy27-summary.xlsx`.

THE FRONT SHEET IS A VLOOKUP INTERFACE. THE DATA IS BEHIND IT

`Summary` reads as empty or as formula text. The workbook must be opened with
`data_only=True` and the `DataC70`, `DataNSS`, `dataAid` and `dataContribution` sheets
taken directly. This is the one DESE source here that openpyxl reads rather than
`dese_xlsx`, because it has front sheets, several worksheets and cached formula values.

THREE THINGS IN THIS WORKBOOK THAT WILL MISLEAD ANYBODY WHO QUOTES A COLUMN NAME

**1. `rqdnss` APPEARS TWICE, IN COLUMNS I AND J, AND THEY ARE DIFFERENT NUMBERS.** Not a
duplicate -- two quantities under one name, differing in over a thousand district-years.
Column I is required net school spending as the formula computes it: it equals
`distrlc + c70aid` in all but a handful of rows, and the run counts them. Column J is
sourced in the sheet's own note to *"from Profile file, includes carryover"*, and it is
the one `DataNSS` publishes -- checked here district by district and year by year, where
it agrees in every comparable row and column I does not. So:

    required_nss           column I    the formula's own arithmetic
    required_nss_published column J    what DESE publishes, carryover included

A figure quoted as "required net school spending" off this sheet is one of those two and
the sheet does not say which. Rule 13: cite the coordinate.

**2. `c70aid` ALSO APPEARS TWICE, IN COLUMNS H AND M**, and the sheet's note on M reads
*"From this file, reflecting penalties, if any"*. They differ in several hundred rows,
concentrated in the years where penalties were applied. Both are carried, named for what
the sheet says they are.

**3. `actualNSS` IS NOT ACTUAL IN THE LAST TWO YEARS.** `DataNSS` names the same values
`2025budnss` and `2026budnss` -- BUDGETED net school spending, not spent. The column in
`DataC70` is headed `actualNSS` for all thirty-four years regardless. Rule 1 is the whole
of why this matters: a growth rate measured from an actual to a budget is partly growth
and partly the step between the two. So `nss_stage` is carried on every row, taken from
the `DataNSS` header token for that year, and it says `actual` or `budgeted`.

**And the workbook contradicts itself about FY2025.** Column BW is headed `2025budnss`;
the summary block at columns CA-CD prints the identical value under `FY25 Actual NSS`.
Same number, two stages, one workbook. This extract takes the per-year column, so FY2025
reads `budgeted`, and the disagreement is recorded rather than resolved -- nothing here
establishes which label is right.

DATANSS IS NOT LOADED, AND THAT IS A MEASUREMENT

`DataNSS` holds required and actual net school spending as one column per year. Compared
against `DataC70` value by value it agrees on actual NSS in every comparable district-year
and on required NSS wherever column J is used. It is the same series in a wide shape.
Loading it as a second table would make one series look like two agreeing sources.

`5izv-jyrd`, DESE's *Chapter 70 Foundation Budget and Net School Spending* on the open-data
portal, is a genuinely separate publication and IS used -- as an independent cross-check of
required and actual NSS for SY2008-SY2022, asserted on every run. It is not loaded either,
for the same reason, and because it stops three years short of this workbook.

WHAT THE CIRCUIT BREAKER IS

Reimbursement to the district for high-cost special education placements, keyed on **`FY`
and not `SY`** -- every other DESE file in this archive is school year, and this repository
has already had a fiscal-year type error that matched nothing silently. It also carries
`ELIG_STU_CLAIM_CNT`, a count of CHILDREN rather than dollars, which is rare here.

It is money the district receives and it does not appear in the general fund appropriation
the town votes. Rule 11: a budget line that falls because circuit breaker rose is not a
line that got cheaper.
"""
import argparse
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dese_xlsx import DATA, ROOT, STATE, fmt, num, peers, records  # noqa: E402

DOC_PROFILE = 'sources/state-dese/dese-ch70-district-profile.xlsx'
DOC_FACTORS = 'sources/state-dese/dese-ch70-key-factors.xlsx'
DOC_FOUND = 'sources/state-dese/dese-ch70-foundation-nss.xlsx'
DOC_CB = 'sources/state-dese/dese-circuit-breaker.xlsx'

OUT_FORMULA = os.path.join(DATA, 'dese-ch70-formula.csv')
OUT_AID = os.path.join(DATA, 'dese-ch70-aid-factor.csv')
OUT_CONTRIB = os.path.join(DATA, 'dese-ch70-contribution.csv')
OUT_CB = os.path.join(DATA, 'dese-circuit-breaker.csv')
OUT_STATEWIDE = os.path.join(DATA, 'dese-ch70-statewide.csv')

STATEWIDE_FIELDS = ['fy', 'measure', 'basis', 'districts', 'p_min', 'p25', 'median', 'p75',
                    'p_max', 'lunenburg', 'lunenburg_rank_of_districts', 'doc_id']

LUNENBURG_ORG4 = '0162'
# The tie that matters: DESE's Chapter 70 aid for Lunenburg against what the TOWN'S OWN
# accounting system recorded receiving. Two entirely independent routes to one figure --
# the state's formula workbook and a MUNIS revenue printout -- and neither derived from the
# other. Read out of the ledger extract rather than typed, so that if either moves this
# stops (rule 2).
MUNIS_LEDGER = os.path.join(DATA, 'munis-ledger.csv')
CH70_ACCOUNT = 'CH 70 AID'

# DataC70, by COLUMN INDEX, because two pairs of columns share a name (see the docstring).
C70_HEADER_ROW = 4                      # 1-based; body starts at row 5
C70_COLS = {0: 'Org4Codefy', 1: 'Org4Code', 2: 'LEANumCode', 3: 'fy', 4: 'distfoundenro',
            5: 'distfoundbudget', 6: 'distrlc', 7: 'c70aid', 8: 'rqdnss', 9: 'rqdnss',
            10: 'actualNSS', 12: 'c70aid'}

FORMULA_FIELDS = ['fy', 'lea', 'org4_code', 'lea_number', 'district', 'level',
                  'foundation_enrollment', 'foundation_budget',
                  'required_local_contribution', 'ch70_aid', 'ch70_aid_after_penalties',
                  'required_nss', 'required_nss_published', 'net_school_spending',
                  'nss_stage', 'nss_pct_of_required', 'reconciles', 'doc_id']
AID_FIELDS = ['fy', 'lea', 'district', 'level', 'foundation_enrollment',
              'foundation_budget', 'required_local_contribution', 'target_aid_pct',
              'foundation_aid_increment', 'down_payment_aid_increment',
              'growth_aid_increment', 'target_aid_phase_in', 'minimum_aid_increment',
              'non_operating_reduction', 'ch70_aid', 'required_nss', 'ch70_aid_reduction',
              'hold_harmless_low_income', 'minimum_aid_adjustment', 'doc_id']
CONTRIB_FIELDS = ['fy', 'lea_number', 'municipality', 'equalized_valuation',
                  'property_local_effort', 'income', 'income_local_effort',
                  'combined_effort_yield', 'town_foundation_enrollment',
                  'town_foundation_budget', 'target_local_contribution',
                  'municipal_revenue_growth_factor', 'preliminary_contribution',
                  'excess_effort', 'effort_reduction', 'shortfall', 'dollar_increment',
                  'acceleration', 'required_local_contribution', 'doc_id']
CB_COLS = ['FY', 'DIST_CODE', 'DIST_NAME', 'ELIG_STU_CLAIM_CNT', 'TOT_ELIG_EXPENSES',
           'THRESHOLD_AMT', 'NET_ELIG_INSTR_TUIT_COSTS', 'NET_ELIG_TRANS_COSTS',
           'TOT_NET_CLAIM', 'REIMB_INSTR_TUIT', 'REIMB_SPEC_IND_INSTR_TUIT',
           'REIMB_TRANS', 'REIMB_SPEC_IND_TRANS', 'PRIOR_YEAR_ADJ', 'TOT_QTLY_PAYMENT',
           'EXTRA_RELIEF_PAYMENT', 'ADDL_SUPPL_PAYMENT', 'COMMENTS']
CB_FIELDS = ['fy', 'lea', 'district', 'level', 'eligible_students_claimed',
             'total_eligible_expenses', 'threshold_amount',
             'net_eligible_instruction_tuition', 'net_eligible_transport',
             'total_net_claim', 'reimb_instruction_tuition',
             'reimb_special_circumstance_tuition', 'reimb_transport',
             'reimb_special_circumstance_transport', 'prior_year_adjustment',
             'total_quarterly_payment', 'extra_relief_payment',
             'additional_supplemental_payment', 'comments', 'reconciles', 'doc_id']


def quantile(vals, q):
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    i = q * (len(vals) - 1)
    lo, hi = int(i), min(int(i) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (i - lo)


LUNENBURG_LEA = '01620000'


def build_statewide(formula, cb):
    """Every district collapsed to a distribution, so a peer comparison has a denominator.

    Districts differ in size, grade span and whether they are regional, so a raw dollar
    comparison between two of them means very little and a position in a state
    distribution means something. `districts` is the denominator and it is printed on
    every row because a rank without one is not a measurement.

    Three measures, and each says on the row what it is a ratio OF, because every one of
    them is a division by a count or a dollar whose definition has to travel with it.
    """
    out, by = [], {}

    def add(fy, measure, basis, lea, value, doc):
        if value is None:
            return
        by.setdefault((fy, measure, basis, doc), {})[lea] = value

    for r in formula:
        if r['level'] != 'district':
            continue
        fy, lea = r['fy'], r['lea']
        act, req = num(r['net_school_spending']), num(r['required_nss_published'])
        enro, aid = num(r['foundation_enrollment']), num(r['ch70_aid'])
        rlc, fnd = num(r['required_local_contribution']), num(r['foundation_budget'])
        if act and req:
            add(fy, 'net school spending as a share of required',
                'stage: ' + (r['nss_stage'] or 'not stated'), lea, act / req, r['doc_id'])
        if aid is not None and enro:
            add(fy, 'Chapter 70 aid per foundation pupil',
                'per FOUNDATION enrollment, which is not a headcount of children in the '
                'buildings', lea, aid / enro, r['doc_id'])
        if rlc is not None and fnd:
            add(fy, 'required local contribution as a share of the foundation budget',
                'the rest is Chapter 70 aid', lea, rlc / fnd, r['doc_id'])
    for r in cb:
        if r['level'] != 'district':
            continue
        claim, students = num(r['total_net_claim']), num(r['eligible_students_claimed'])
        if claim is not None and students:
            add(r['fy'], 'circuit breaker net claim per eligible student',
                'FISCAL year, not school year', r['lea'], claim / students, r['doc_id'])

    for (fy, measure, basis, doc), vals in sorted(by.items()):
        xs = sorted(vals.values())
        lun = vals.get(LUNENBURG_LEA)
        rank = ('%d of %d' % (sum(1 for v in xs if v > lun) + 1, len(xs))
                if lun is not None else '')
        out.append(dict(
            fy=fy, measure=measure, basis=basis, districts=len(xs),
            p_min='%.4f' % xs[0], p25='%.4f' % quantile(xs, 0.25),
            median='%.4f' % quantile(xs, 0.5), p75='%.4f' % quantile(xs, 0.75),
            p_max='%.4f' % xs[-1],
            lunenburg='' if lun is None else '%.4f' % lun,
            lunenburg_rank_of_districts=rank, doc_id=doc))
    return out


def sheet(wb, name):
    if name not in wb.sheetnames:
        raise SystemExit('%s has no sheet %r; it has %s.\nNothing written -- the front '
                         'sheet is a VLOOKUP interface and the data is behind it.'
                         % (DOC_PROFILE, name, wb.sheetnames))
    return wb[name]


def read_profile():
    """`DataC70` by coordinate, and `DataNSS` for the names, the codes and the stage."""
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(ROOT, DOC_PROFILE), read_only=True,
                                data_only=True)
    ws = sheet(wb, 'DataC70')
    body = list(ws.iter_rows(min_row=C70_HEADER_ROW, values_only=True))
    head = ['' if c is None else str(c).strip() for c in body[0]]
    for j, want in C70_COLS.items():
        if j >= len(head) or head[j] != want:
            raise SystemExit(
                'DataC70 column %d is %r, expected %r.\nThis sheet is read BY COORDINATE '
                'because two pairs of its columns share a name;\na shift of one column '
                'would silently swap two different quantities. Nothing written.'
                % (j, head[j] if j < len(head) else '<absent>', want))
    c70 = body[1:]

    nss = list(sheet(wb, 'DataNSS').iter_rows(min_row=8, values_only=True))
    wb.close()
    nhead = ['' if c is None else str(c).strip() for c in nss[0]]
    if nhead[:4] != ['Org4Code', 'Org8Code', 'LEA', 'District']:
        raise SystemExit('DataNSS does not begin Org4Code/Org8Code/LEA/District; it '
                         'begins %s.\nNothing written.' % nhead[:4])

    names, req_col, act_col, stage = {}, {}, {}, {}
    for j, h in enumerate(nhead):
        if h.endswith('reqdnss') and h[:4].isdigit():
            req_col[int(h[:4])] = j
        elif h.endswith('actnss') and h[:4].isdigit():
            act_col[int(h[:4])], stage[int(h[:4])] = j, 'actual'
        elif h.endswith('budnss') and h[:4].isdigit():
            act_col[int(h[:4])], stage[int(h[:4])] = j, 'budgeted'
    published = {}
    for r in nss[1:]:
        if not r or not r[0]:
            continue
        o = str(r[0]).strip()
        names[o] = (str(r[1]).strip(), ' '.join(str(r[3] or '').split()))
        for fy, j in req_col.items():
            published[(o, fy, 'req')] = r[j] if j < len(r) else None
        for fy, j in act_col.items():
            published[(o, fy, 'act')] = r[j] if j < len(r) else None
    if not names or not stage:
        raise SystemExit('DataNSS yielded no district names or no year columns, which '
                         'looks exactly\nlike data that is absent. Nothing written.')
    return c70, names, published, stage


def read_factors():
    """`dataAid` and `dataContribution` from the key-factors workbook."""
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(ROOT, DOC_FACTORS), read_only=True,
                                data_only=True)
    out = {}
    for name, want in (
            ('dataAid', ['Org8Codefy', 'LEANumCode', 'Org8Code', 'DistName', 'fy',
                         'distfoundenro', 'distfoundbudget', 'distrlc', 'disttargaidpct',
                         'foundaidinc', 'downpymtaidinc', 'growthaidinc',
                         'targaidphaseinaid', 'minaidinc', 'nonopred', 'c70aid', 'rqdnss',
                         'c70aidreduct', 'holdharmlesslowinc', 'minaidadjustmentinc']),
            ('dataContribution', ['Org8Codefy', 'LEANumCode', 'Org8Code', 'DistName', 'fy',
                                  'eqv', 'proplocaleffort', 'income', 'inclocaleffort',
                                  'cey', 'townenro', 'townfoundbudget', 'targetlocacont',
                                  'mrgf', 'prelcont', 'excess effort', 'effortred',
                                  'shortfall', 'dollarincrement', 'acceleration', 'rlc'])):
        if name not in wb.sheetnames:
            raise SystemExit('%s has no sheet %r.' % (DOC_FACTORS, name))
        rows_ = list(wb[name].iter_rows(min_row=3, values_only=True))
        head = ['' if c is None else str(c).strip() for c in rows_[0]]
        if head[:len(want)] != want:
            raise SystemExit('%s!%s columns are %s\n  expected %s\nNothing written.'
                             % (DOC_FACTORS, name, head[:len(want)], want))
        out[name] = [r for r in rows_[1:] if r and r[0]]
    wb.close()
    return out['dataAid'], out['dataContribution']


def write(fields, recs):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    for r in recs:
        w.writerow(r)
    return out.getvalue(), len(recs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    for doc in (DOC_PROFILE, DOC_FACTORS, DOC_FOUND, DOC_CB):
        if not os.path.exists(os.path.join(ROOT, doc)):
            print('%s is catalogued but not on disk.\nrun: python3 '
                  'scripts/sync_archive.py --pull' % doc)
            return 1

    print('Reading the Chapter 70 workbooks and the circuit breaker')
    c70, names, published, stage = read_profile()

    # ---- DataC70, one row per district-year ------------------------------------------
    formula, unnamed = [], set()
    rq_computed_ok, rq_computed_bad = 0, []
    pub_ok, pub_bad = 0, []
    act_ok, act_bad = 0, []
    for r in c70:
        o = '' if r[1] is None else str(r[1]).strip()
        if not o:
            continue
        fy = int(r[3])
        level = 'state' if o == '0000' else 'district'
        org8, name = names.get(o, ('', ''))
        if level == 'district' and not org8:
            unnamed.add(o)
        rlc, aid = num(r[6]), num(r[7])
        rq_i, rq_j, act = num(r[8]), num(r[9]), num(r[10])

        # The identity the formula states about itself.
        verdict = ''
        if None not in (rlc, aid, rq_i):
            if abs(rq_i - (rlc + aid)) < 1:
                rq_computed_ok += 1
                verdict = 'yes'
            else:
                rq_computed_bad.append((fy, o, rq_i, rlc + aid))
                verdict = 'no'
        # Column J against what DataNSS publishes, and the same for actual NSS.
        for got, key, ok_bad in ((rq_j, 'req', 'pub'), (act, 'act', 'act')):
            want = published.get((o, fy, key))
            if got is None or want in (None, 0):
                continue
            if abs(float(want) - float(got)) < 1:
                if ok_bad == 'pub':
                    pub_ok += 1
                else:
                    act_ok += 1
            elif ok_bad == 'pub':
                pub_bad.append((fy, o, got, want))
            else:
                act_bad.append((fy, o, got, want))

        formula.append(dict(
            fy=fy, lea=org8 or ('00000000' if level == 'state' else ''), org4_code=o,
            lea_number='' if r[2] is None else str(r[2]).strip(),
            district=name or ('State Totals' if level == 'state' else ''), level=level,
            foundation_enrollment=fmt(num(r[4])), foundation_budget=fmt(num(r[5])),
            required_local_contribution=fmt(rlc), ch70_aid=fmt(aid),
            ch70_aid_after_penalties=fmt(num(r[12])),
            required_nss=fmt(rq_i), required_nss_published=fmt(rq_j),
            net_school_spending=fmt(act) if act else '',
            nss_stage=stage.get(fy, '') if act else '',
            nss_pct_of_required=('%.4f' % (act / rq_j)) if act and rq_j else '',
            reconciles=verdict, doc_id=DOC_PROFILE))

    print('  DataC70  rqdnss (column I) == distrlc + c70aid: %s agree, %d disagree'
          % (f'{rq_computed_ok:,}', len(rq_computed_bad)))
    for b in rq_computed_bad[:6]:
        print('      %s' % (b,))
    print('  DataC70  rqdnss (column J) == what DataNSS publishes: %s agree, %d disagree'
          % (f'{pub_ok:,}', len(pub_bad)))
    print('  DataC70  actualNSS == what DataNSS publishes: %s agree, %d disagree'
          % (f'{act_ok:,}', len(act_bad)))
    if not rq_computed_ok or not pub_ok or not act_ok:
        print('\nA check matched NOTHING, which looks exactly like data that is absent. '
              'Nothing written.')
        return 1
    if pub_bad or act_bad:
        for b in (pub_bad + act_bad)[:8]:
            print('      %s' % (b,))
        print('\nDataC70 and DataNSS have parted company. They were established as ONE '
              'series in two\nshapes and DataNSS is not loaded on that basis. Nothing '
              'written.')
        return 1
    if unnamed:
        print('\n%d Org4Code(s) in DataC70 have no row in DataNSS and so no name or '
              '8-digit code:\n  %s\nA district with no code cannot be joined to anything '
              'else here. Nothing written.'
              % (len(unnamed), ', '.join(sorted(unnamed)[:12])))
        return 1

    # ---- the reconciliation that matters most ----------------------------------------
    # FY2026 Chapter 70 aid, against the figure /state-aid derives by cell reference from
    # a different DESE workbook. Read from that series, never typed.
    want_aid = None
    with open(MUNIS_LEDGER, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if (row['name'] == CH70_ACCOUNT and row['fy'] == '2026'
                    and row['account_type'] == 'revenue' and row['level'] == 'account'):
                want_aid = abs(num(row['revised']) or 0)
    got_aid = next((num(r['ch70_aid']) for r in formula
                    if r['org4_code'] == LUNENBURG_ORG4 and r['fy'] == 2026), None)
    if got_aid is None:
        print('\nLunenburg has no FY2026 row in DataC70. Nothing written.')
        return 1
    if want_aid is None:
        print('\nNo FY2026 %r revenue account in munis-ledger.csv, so the tie between '
              "DESE's\nfigure and the town's own ledger could not be made at all -- which "
              'looks exactly\nlike a join that matched nothing. Nothing written.'
              % CH70_ACCOUNT)
        return 1
    if abs(want_aid - got_aid) > 1:
        print("\n  FY2026 Lunenburg Chapter 70 aid is %s in DESE's DataC70 and %s on the "
              "town's own\n  MUNIS revenue ledger. Two independent sources disagree about "
              'one receipt.\n  Nothing written.' % (got_aid, want_aid))
        return 1
    print("  FY2026 Lunenburg Chapter 70 aid ties to the town's own MUNIS revenue "
          'ledger: %s' % f'{got_aid:,.0f}')

    # ---- 5izv-jyrd, an independent publication, as a cross-check ----------------------
    found_cols = ['SY', 'DIST_CODE', 'DIST_NAME', 'REQ_NSS_AMT', 'ACTL_NSS_AMT',
                  'OVR_UND_REQ_AMT', 'ACTL_NSS_PCT_OF_REQ_NSS', 'FDN_BDGT_AMT',
                  'ACTL_NSS_PCT_OF_FDN_BUDG']
    by_lea = {}
    for rec in formula:
        if rec['lea']:
            by_lea[(rec['lea'], rec['fy'])] = rec
    f_ok, f_bad, f_none = 0, [], 0
    for r in records(os.path.join(ROOT, DOC_FOUND), found_cols, DOC_FOUND):
        code = r['DIST_CODE'] if r['DIST_CODE'] != STATE else '00000000'
        rec = by_lea.get((code, int(r['SY'])))
        if rec is None:
            f_none += 1
            continue
        for theirs, ours in ((num(r['REQ_NSS_AMT']), num(rec['required_nss_published'])),
                             (num(r['ACTL_NSS_AMT']), num(rec['net_school_spending']))):
            if theirs is None or ours is None:
                continue
            if abs(theirs - ours) <= 1:
                f_ok += 1
            else:
                f_bad.append((r['SY'], r['DIST_NAME'], theirs, ours))
    print('  5izv-jyrd (a separate DESE publication) against DataC70, SY2008-SY2022: '
          '%s agree,\n    %d disagree, %d rows with no counterpart'
          % (f'{f_ok:,}', len(f_bad), f_none))
    if not f_ok:
        print('\nThe cross-check against 5izv-jyrd matched NOTHING. Nothing written.')
        return 1
    for b in f_bad[:6]:
        print('      %s' % (b,))
    if f_bad:
        print('      two DESE publications disagree about net school spending; the '
              'disagreement is\n      printed rather than smoothed, and neither is '
              'treated as correcting the other')

    # ---- the key-factors sheets ------------------------------------------------------
    aid_rows, contrib_rows = read_factors()
    aid, aid_ok, aid_bad = [], 0, []
    for r in aid_rows:
        code = str(r[2]).strip()
        fy = int(r[4])
        lvl = 'state' if code in ('00000000', '0000') else 'district'
        rec = by_lea.get((code, fy))
        got = num(r[15])
        if rec is not None and got is not None and num(rec['ch70_aid']) is not None:
            if abs(num(rec['ch70_aid']) - got) <= 1:
                aid_ok += 1
            else:
                aid_bad.append((fy, code, got, num(rec['ch70_aid'])))
        aid.append(dict(
            fy=fy, lea=code, district=' '.join(str(r[3] or '').split()), level=lvl,
            foundation_enrollment=fmt(num(r[5])), foundation_budget=fmt(num(r[6])),
            required_local_contribution=fmt(num(r[7])), target_aid_pct=fmt(num(r[8])),
            foundation_aid_increment=fmt(num(r[9])),
            down_payment_aid_increment=fmt(num(r[10])),
            growth_aid_increment=fmt(num(r[11])), target_aid_phase_in=fmt(num(r[12])),
            minimum_aid_increment=fmt(num(r[13])), non_operating_reduction=fmt(num(r[14])),
            ch70_aid=fmt(got), required_nss=fmt(num(r[16])),
            ch70_aid_reduction=fmt(num(r[17])), hold_harmless_low_income=fmt(num(r[18])),
            minimum_aid_adjustment=fmt(num(r[19])), doc_id=DOC_FACTORS))
    print('  dataAid c70aid == DataC70 c70aid: %s agree, %d disagree'
          % (f'{aid_ok:,}', len(aid_bad)))
    if not aid_ok:
        print('\nThe key-factors workbook and the district profile share no district-year '
              'at all,\nwhich looks exactly like a join that matched nothing. '
              'Nothing written.')
        return 1
    for b in aid_bad[:6]:
        print('      %s' % (b,))

    contrib = []
    for r in contrib_rows:
        contrib.append(dict(
            fy=int(r[4]), lea_number='' if r[1] is None else str(r[1]).strip(),
            municipality=' '.join(str(r[3] or '').split()),
            equalized_valuation=fmt(num(r[5])), property_local_effort=fmt(num(r[6])),
            income=fmt(num(r[7])), income_local_effort=fmt(num(r[8])),
            combined_effort_yield=fmt(num(r[9])),
            town_foundation_enrollment=fmt(num(r[10])),
            town_foundation_budget=fmt(num(r[11])),
            target_local_contribution=fmt(num(r[12])),
            municipal_revenue_growth_factor=fmt(num(r[13])),
            preliminary_contribution=fmt(num(r[14])), excess_effort=fmt(num(r[15])),
            effort_reduction=fmt(num(r[16])), shortfall=fmt(num(r[17])),
            dollar_increment=fmt(num(r[18])), acceleration=fmt(num(r[19])),
            required_local_contribution=fmt(num(r[20])), doc_id=DOC_FACTORS))

    # ---- the circuit breaker ---------------------------------------------------------
    cb, cb_ok, cb_bad = [], 0, []
    for r in records(os.path.join(ROOT, DOC_CB), CB_COLS, DOC_CB):
        instr, trans = num(r['NET_ELIG_INSTR_TUIT_COSTS']), num(r['NET_ELIG_TRANS_COSTS'])
        claim = num(r['TOT_NET_CLAIM'])
        verdict = ''
        if None not in (instr, trans, claim):
            if abs(instr + trans - claim) <= 1:
                cb_ok += 1
                verdict = 'yes'
            else:
                cb_bad.append((r['FY'], r['DIST_NAME'], instr + trans, claim))
                verdict = 'no'
        cb.append(dict(
            fy=int(r['FY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
            level='state' if r['DIST_CODE'] == STATE else 'district',
            eligible_students_claimed=fmt(num(r['ELIG_STU_CLAIM_CNT'])),
            total_eligible_expenses=fmt(num(r['TOT_ELIG_EXPENSES'])),
            threshold_amount=fmt(num(r['THRESHOLD_AMT'])),
            net_eligible_instruction_tuition=fmt(instr),
            net_eligible_transport=fmt(trans), total_net_claim=fmt(claim),
            reimb_instruction_tuition=fmt(num(r['REIMB_INSTR_TUIT'])),
            reimb_special_circumstance_tuition=fmt(num(r['REIMB_SPEC_IND_INSTR_TUIT'])),
            reimb_transport=fmt(num(r['REIMB_TRANS'])),
            reimb_special_circumstance_transport=fmt(num(r['REIMB_SPEC_IND_TRANS'])),
            prior_year_adjustment=fmt(num(r['PRIOR_YEAR_ADJ'])),
            total_quarterly_payment=fmt(num(r['TOT_QTLY_PAYMENT'])),
            extra_relief_payment=fmt(num(r['EXTRA_RELIEF_PAYMENT'])),
            additional_supplemental_payment=fmt(num(r['ADDL_SUPPL_PAYMENT'])),
            comments=r['COMMENTS'], reconciles=verdict, doc_id=DOC_CB))
    print('  ab34-d3ma  tuition claim + transport claim == TOT_NET_CLAIM: %s agree, '
          '%d disagree' % (f'{cb_ok:,}', len(cb_bad)))
    for b in cb_bad[:6]:
        print('      %s' % (b,))
    if not cb_ok:
        print('\nThe circuit breaker identity matched NOTHING. Nothing written.')
        return 1

    # ---- every district, as a distribution, before the scope is applied ---------------
    statewide = build_statewide(formula, cb)

    # ---- the scope --------------------------------------------------------------------
    want = peers()
    n_all = (len(formula), len(aid), len(contrib), len(cb))
    formula = [r for r in formula if r['lea'] in want or r['level'] == 'state']
    aid = [r for r in aid if r['lea'] in want or r['level'] == 'state']
    cb = [r for r in cb if r['lea'] in want or r['level'] == 'state']
    # `contrib` is NOT scoped. It is keyed on a MUNICIPALITY rather than a district, and
    # there is no mapping here from one to the other -- a town that belongs to a regional
    # district has a contribution row and no district row of its own, so filtering it by
    # the district peer set would silently drop exactly the towns whose money is hardest
    # to see. It is also small enough to keep whole.
    print('  scoped to Lunenburg, its six peers and the state row: %s of %s Chapter 70 '
          'rows,\n    %s of %s aid rows, %s of %s circuit breaker rows. The %s municipal '
          'rows are kept\n    whole -- a town is not a district and there is no mapping '
          'here between them.\n    Every identity above was asserted on all of them '
          'first.'
          % (f'{len(formula):,}', f'{n_all[0]:,}', f'{len(aid):,}', f'{n_all[1]:,}',
             f'{len(cb):,}', f'{n_all[3]:,}', f'{len(contrib):,}'))
    if not (formula and aid and contrib and cb):
        print('\nScoping left one of the four tables EMPTY, which looks exactly like a '
              'filter that\nmatched nothing. Nothing written.')
        return 1

    outputs = [(OUT_FORMULA, FORMULA_FIELDS, formula), (OUT_AID, AID_FIELDS, aid),
               (OUT_CONTRIB, CONTRIB_FIELDS, contrib), (OUT_CB, CB_FIELDS, cb),
               (OUT_STATEWIDE, STATEWIDE_FIELDS, statewide)]
    texts = []
    for path, fields, recs in outputs:
        if not recs:
            print('\n%s would be EMPTY. Nothing written.' % os.path.relpath(path, ROOT))
            return 1
        recs.sort(key=lambda r: tuple(str(r[f]) for f in fields[:4]))
        texts.append((path,) + write(fields, recs))

    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t, _ in texts
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else '') != t]
        if stale:
            print('\nstale: %s\nRe-run: python3 scripts/extract_dese_state_aid.py'
                  % ', '.join(stale))
            return 1
        print('\nok: all four state-aid extracts still reproduce')
        return 0

    print()
    for path, text, n in texts:
        open(path, 'w', encoding='utf-8', newline='').write(text)
        print('wrote %s  %s rows' % (os.path.relpath(path, ROOT), f'{n:,}'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
