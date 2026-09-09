#!/usr/bin/env python3
"""DESE's function-code expenditures, with the hierarchy made explicit before anything is summed.

    python3 scripts/extract_dese_finance.py
    python3 scripts/extract_dese_finance.py --check

Writes two files:

  sources/data/dese-function-expenditure.csv   Lunenburg and its six peers, every row
  sources/data/dese-function-statewide.csv     every district collapsed to a distribution

THE TRAP THIS FILE EXISTS TO CLOSE

`cnfs-edqq` puts ROLLUP rows and DETAIL rows in the same table and **nothing in the column
names says which is which.** Summing every row for Lunenburg SY2025 gives $116,065,166 for
a district whose in-district spending is $27,903,187 -- the same number counted up to four
times. A plausible total produced by double counting is the worst outcome available here,
and this project has shipped one before.

So the level is a COLUMN, derived per row, and the loader refuses to write if any row
cannot be classified.

THE HIERARCHY, AND HOW IT WAS ESTABLISHED

Not read off a data dictionary -- DESE publishes none for this file. Derived from the data
and then asserted, on all 363,514 rows and all 5,479 district-years:

1.  Three tests agree perfectly on which rows are summaries: `FUNC_CODE == FUNC_CAT_CODE`,
    `FUNC_CODE` being alphabetic rather than numeric, and `IN_OUT_DIST` being blank.
    75,822 rows pass all three, 287,692 fail all three, and none is ambiguous. The script
    asserts all three agree rather than picking one, so a change in any of them is caught.

2.  Each of the ten in-district categories equals the sum of its own detail rows.
3.  Those ten sum to `IIII`, In-district Expenditure.
4.  `TUIT` detail plus `ODTR` equals `OODD`, Out-of-district Expenditure. Note the shape:
    **`TUIT` has no category row at all** -- its details roll straight into `OODD` -- and
    `ODTR` is a category with no parent of its own beyond `OODD`.
5.  `IIII` + `OODD` = `TTPP`, the grand total. `ODTR` is inside `OODD`, so adding it again
    double counts.

2 through 5 hold in every district-year to within $4, which is what rounding ten
whole-dollar components can produce. Nothing here is off by more than that -- with one
exception, below, which is not rounding.

THE ONE PLACE DETAIL DOES NOT SUM TO ITS CATEGORY

`ODTR`, out-of-district transportation, is PARTIALLY itemised. In 43 district-years a
single detail row appears, always function 9130 `Charter Transportation Tuition`, and it
is a component rather than the whole: Boston SY2024 prints $215,512 of 9130 against an
`ODTR` category of $37,967,473. The rest of out-of-district transportation has no printed
detail row anywhere. So the check on `ODTR` is containment, not equality, and the row's
`reconciles` column says `partial` rather than `yes`. Summing 9130 as though it were
out-of-district transportation understates it by up to $37.7M.

WHAT THIS DATA IS

`GEN_FUND` and `GRNTS_REVOLV` are separate columns. That is the split rule 11 says nobody
publishes, and it is real -- but read what it is keyed on. It is a split by DESE FUNCTION
CODE, and a function code is not a budget line and not a post. Lunenburg SY2025 shows
$478,097 of grant and revolving money against function 2330, Paraprofessionals, beside
$1,338,477 of general fund. That bounds the paraprofessional question; it does not settle
it, because nothing here says which paraprofessional, or which grant, or whether the same
posts were general-funded the year before. See `sources/data/money-gaps.csv`.

It is also SPENDING, not appropriation, and it is DESE's definition of the district rather
than the town's: it carries town-paid insurance and retirement attributed to the schools,
which is $3,459 per pupil for Lunenburg in SY2025 on its own. It must never be subtracted
from the town's appropriation to produce "hidden money".

WHY ONLY SEVEN DISTRICTS IN THE ROW-LEVEL FILE

363,514 rows would take the published database past Cloudflare's 25MB per-asset limit --
the same trade `extract_dese_radar.py` records. So the row-level extract is Lunenburg and
the six peers this project already compares against, and every other district is kept as a
DISTRIBUTION in the second file: the median, quartiles and range of per-pupil spending per
function per year, with Lunenburg's rank. That is what a peer comparison actually needs,
and it is what rule 6 asks for -- districts differ in size, grade span and whether they
are regional, so a raw dollar comparison between two of them means very little and a
per-pupil position in a state distribution means something.

The full workbook is in the archive with its sha256 and its address, so anyone wanting
another district has the file we used.
"""
import argparse
import csv
import io
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
DOC = 'sources/state-dese/district-expenditures-by-function.xlsx'
SRC = os.path.join(ROOT, DOC)
OUT_ROWS = os.path.join(DATA, 'dese-function-expenditure.csv')
OUT_STATE = os.path.join(DATA, 'dese-function-statewide.csv')
RADAR = os.path.join(DATA, 'dese-radar.csv')

# The comparison set this project already uses, read out of dese-radar.csv rather than
# retyped -- three of the first eight codes written from memory in the radar extract were
# invented, and only a reconciliation caught them.
LUNENBURG = '01620000'

# The ten in-district function categories, named rather than inferred from position.
IN_DISTRICT = ['ADMN', 'LDRS', 'TCHR', 'TSER', 'PDEV', 'MATL', 'GUID', 'SERV',
               'OPMN', 'BENE']
# Community Activities. Six rows in the whole file, two virtual schools, always inside
# IIII. Named so that a row carrying it is classified rather than refused.
EXTRA_IN_DISTRICT = ['COMM']
# Out-of-district. TUIT has detail rows and NO category row of its own; ODTR has a
# category row and only a partial itemisation beneath it.
OUT_TUITION = 'TUIT'
OUT_TRANSPORT = 'ODTR'
ROLLUPS = {'IIII': 'In-district Expenditure', 'OODD': 'Out-of-district Expenditure'}
GRAND = 'TTPP'

# Ten whole-dollar components, each rounded independently, can miss their printed sum by
# a few dollars. Four is the largest difference in the file and it is not exceeded.
TOL = 4

FIELDS = ['fy', 'lea', 'district', 'level', 'func_cat_code', 'func_cat_desc', 'func_code',
          'func_desc', 'in_out_dist', 'gen_fund', 'grants_revolving', 'total',
          'per_pupil', 'reconciles', 'doc_id']
STATE_FIELDS = ['fy', 'level', 'func_cat_code', 'func_code', 'func_desc', 'districts',
                'gen_fund_total', 'grants_revolving_total', 'total', 'grant_share',
                'per_pupil_basis', 'per_pupil_min', 'per_pupil_p25', 'per_pupil_median',
                'per_pupil_p75', 'per_pupil_max', 'lunenburg_per_pupil',
                'lunenburg_rank_of_districts', 'doc_id']


def peers():
    """Lunenburg plus the COMPARISON districts dese-radar.csv carries.

    NOT every district in that file. It also carries the DESTINATIONS -- where Lunenburg
    children actually go -- and a destination is not a peer. The roles are declared in
    extract_dese_radar.py; reading the set back off the whole file made the archive
    growing into the comparison set growing, which is not the same thing.
    """
    from extract_dese_radar import PEERS
    seen = {}
    with open(RADAR, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['lea'] in PEERS:
                seen[r['lea']] = r['district']
    if LUNENBURG not in seen:
        raise SystemExit('dese-radar.csv does not carry Lunenburg; the peer set cannot '
                         'be derived from it. Nothing written.')
    missing = sorted(set(PEERS) - set(seen))
    if missing:
        raise SystemExit('dese-radar.csv is missing peer district(s) %s. Nothing written.'
                         % missing)
    return seen


def money(v):
    v = '' if v is None else str(v).strip()
    if v in ('', 'n/a', 'N/A', '-'):
        return None
    return int(round(float(v)))


def read_workbook():
    import openpyxl
    wb = openpyxl.load_workbook(SRC, read_only=True)
    ws = wb['Data']
    it = ws.iter_rows(values_only=True)
    head = [str(c).strip() for c in next(it)]
    want = ['SY', 'DIST_CODE', 'DIST_NAME', 'FUNC_CAT_CODE', 'FUNC_CAT_DESC', 'FUNC_CODE',
            'FUNC_DESC', 'IN_OUT_DIST', 'GEN_FUND', 'GRNTS_REVOLV', 'TOT_EXP',
            'PER_PUPIL_EXP']
    if head != want:
        raise SystemExit('%s\n  columns are %s\n  expected %s\nNothing written.'
                         % (DOC, head, want))
    out = []
    for r in it:
        if r[0] is None:
            continue
        out.append(dict(zip(head, ['' if c is None else str(c).strip() for c in r])))
    wb.close()
    return out


def classify(r):
    """The level of one row, or an exception naming what could not be classified.

    Three independent tests must agree that a row is a summary. They do, on every row in
    the file; asserting all three rather than trusting one means a change in any of them
    stops the build instead of silently re-levelling the data.
    """
    cat, code, io_ = r['FUNC_CAT_CODE'], r['FUNC_CODE'], r['IN_OUT_DIST']
    by_equal = code == cat
    by_alpha = not code.isdigit()
    by_blank = io_ == ''
    if not (by_equal == by_alpha == by_blank):
        raise ValueError('the three summary tests disagree: FUNC_CAT_CODE=%r '
                         'FUNC_CODE=%r IN_OUT_DIST=%r' % (cat, code, io_))
    if by_equal:
        if cat == GRAND:
            return 'total'
        if cat in ROLLUPS:
            return 'rollup'
        if cat in IN_DISTRICT + EXTRA_IN_DISTRICT + [OUT_TRANSPORT]:
            return 'category'
        raise ValueError('summary row in an unknown category %r' % cat)
    if cat in IN_DISTRICT + [OUT_TUITION, OUT_TRANSPORT]:
        return 'detail'
    raise ValueError('detail row in an unknown category %r (FUNC_CODE %r)' % (cat, code))


def verdicts(rs):
    """Every identity for one district-year, as a verdict per summary row.

    Returns {func_cat_code: 'yes'|'no'|'partial'} and the list of failures.
    """
    summ = {r['FUNC_CAT_CODE']: r for r in rs if r['_level'] != 'detail'}
    det = {}
    for r in rs:
        if r['_level'] == 'detail':
            det.setdefault(r['FUNC_CAT_CODE'], []).append(r)
    out, fails = {}, []
    cols = ['GEN_FUND', 'GRNTS_REVOLV', 'TOT_EXP']

    def diff(got, want):
        return max(abs((money(got[c]) or 0) - (money(want[c]) or 0)) for c in cols)

    def sums(rows_):
        return {c: sum(money(x[c]) or 0 for x in rows_) for c in cols}

    for c in IN_DISTRICT + EXTRA_IN_DISTRICT:
        if c not in summ:
            continue
        if not det.get(c):
            # COMM, and any category a district reports only as a total.
            out[c] = ''
            continue
        d = diff(sums(det[c]), summ[c])
        out[c] = 'yes' if d <= TOL else 'no'
        if d > TOL:
            fails.append(('%s detail does not sum to its category' % c, d))

    # ODTR: containment, never equality. See the module docstring.
    if OUT_TRANSPORT in summ:
        if det.get(OUT_TRANSPORT):
            s = sums(det[OUT_TRANSPORT])
            over = max(s[c] - (money(summ[OUT_TRANSPORT][c]) or 0) for c in cols)
            out[OUT_TRANSPORT] = 'partial'
            if over > TOL:
                fails.append(('ODTR detail EXCEEDS its category', over))
        else:
            out[OUT_TRANSPORT] = ''

    if 'IIII' in summ:
        parts = [summ[c] for c in IN_DISTRICT + EXTRA_IN_DISTRICT if c in summ]
        d = diff(sums(parts), summ['IIII'])
        out['IIII'] = 'yes' if d <= TOL else 'no'
        if d > TOL:
            fails.append(('the in-district categories do not sum to IIII', d))

    if 'OODD' in summ:
        parts = det.get(OUT_TUITION, []) + ([summ[OUT_TRANSPORT]]
                                            if OUT_TRANSPORT in summ else [])
        d = diff(sums(parts), summ['OODD'])
        out['OODD'] = 'yes' if d <= TOL else 'no'
        if d > TOL:
            fails.append(('TUIT detail + ODTR does not sum to OODD', d))

    if GRAND in summ and 'IIII' in summ and 'OODD' in summ:
        d = diff(sums([summ['IIII'], summ['OODD']]), summ[GRAND])
        out[GRAND] = 'yes' if d <= TOL else 'no'
        if d > TOL:
            fails.append(('IIII + OODD does not sum to TTPP', d))
    return out, fails


def cross_check(rows, keep):
    """Two ties to something OUTSIDE this dataset, both required before writing.

    1.  Every per-pupil figure the RADAR workbook prints for the seven districts, against
        the same figure here. Two DESE publications, one from a workbook and one from the
        open-data portal, asserted equal value by value.
    2.  `TOT_EXP / FTE pupils == PER_PUPIL_EXP`, using DESE's own enrollment measure --
        which is what fixes `IIII` as the in-district total rather than one of the other
        rollups. If the hierarchy reading were wrong this would not hold.
    """
    radar = {}
    with open(RADAR, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            radar[(r['lea'], int(r['fy']), r['measure'])] = r['value']
    catmap = {'ADMN': 'Administration', 'LDRS': 'Instructional Leadership',
              'TCHR': 'Teachers', 'TSER': 'Other Teaching Services',
              'PDEV': 'Professional Development',
              'MATL': 'Instructional Materials, Equipment and Technology',
              'GUID': 'Guidance, Counseling and Testing', 'SERV': 'Pupil Services',
              'OPMN': 'Operations and Maintenance',
              'BENE': 'Insurance, Retirement Programs and Other',
              'IIII': 'Total In-District Expenditures', 'TTPP': 'Total Expenditures'}
    pp_ok, pp_bad = 0, []
    fte_ok, fte_bad = 0, []
    for r in rows:
        lea = r['DIST_CODE']
        if lea not in keep or r['_level'] == 'detail':
            continue
        fy = int(r['SY'])
        m = catmap.get(r['FUNC_CAT_CODE'])
        if m:
            want = radar.get((lea, fy, m))
            if want is None:
                pp_bad.append((lea, fy, m, 'absent from dese-radar.csv'))
            elif abs(float(r['PER_PUPIL_EXP'] or 0) - float(want)) > 0.5:
                pp_bad.append((lea, fy, m, r['PER_PUPIL_EXP'], want))
            else:
                pp_ok += 1
        enr = {'IIII': 'In-District FTE Pupils', 'TTPP': 'Total FTE Pupils'}.get(
            r['FUNC_CAT_CODE'])
        if enr:
            n = radar.get((lea, fy, enr))
            if n and float(n) > 0:
                calc = (money(r['TOT_EXP']) or 0) / float(n)
                if abs(calc - float(r['PER_PUPIL_EXP'] or 0)) > 1.0:
                    fte_bad.append((lea, fy, enr, round(calc, 2), r['PER_PUPIL_EXP']))
                else:
                    fte_ok += 1
    return (pp_ok, pp_bad), (fte_ok, fte_bad)


def quantile(vals, q):
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    i = q * (len(vals) - 1)
    lo, hi = int(i), min(int(i) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (i - lo)


def build(rows, keep):
    """The two output files, as text."""
    # Level and verdicts, per district-year.
    groups = {}
    for r in rows:
        r['_level'] = classify(r)
        groups.setdefault((r['SY'], r['DIST_CODE']), []).append(r)

    all_fails, checked = [], 0
    for k, rs in sorted(groups.items()):
        v, fails = verdicts(rs)
        checked += 1
        for r in rs:
            r['_rec'] = '' if r['_level'] == 'detail' else v.get(r['FUNC_CAT_CODE'], '')
        for label, d in fails:
            all_fails.append((k, label, d))

    # ---- the row-level file, seven districts -------------------------------------
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    n_rows = 0
    for r in sorted(rows, key=lambda r: (r['DIST_CODE'], int(r['SY']),
                                         r['FUNC_CAT_CODE'], r['FUNC_CODE'])):
        if r['DIST_CODE'] not in keep:
            continue
        w.writerow(dict(
            fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
            level=r['_level'], func_cat_code=r['FUNC_CAT_CODE'],
            func_cat_desc=r['FUNC_CAT_DESC'], func_code=r['FUNC_CODE'],
            func_desc=r['FUNC_DESC'], in_out_dist=r['IN_OUT_DIST'],
            gen_fund=money(r['GEN_FUND']), grants_revolving=money(r['GRNTS_REVOLV']),
            total=money(r['TOT_EXP']), per_pupil=money(r['PER_PUPIL_EXP']),
            reconciles=r['_rec'], doc_id=DOC))
        n_rows += 1

    # ---- the statewide distribution ----------------------------------------------
    # Grouped on the FULL key including level, so nothing can aggregate a category with
    # its own detail. Per-pupil is only published for in-district rows and the grand
    # total; DESE prints 0 against every out-of-district row, and a median of zeros is
    # not a statistic. `per_pupil_basis` says which it is on every row.
    st = {}
    for r in rows:
        k = (int(r['SY']), r['_level'], r['FUNC_CAT_CODE'], r['FUNC_CODE'])
        s = st.setdefault(k, dict(desc=r['FUNC_DESC'], gen=0, gr=0, tot=0, pp=[],
                                  lun=None, n=0))
        s['n'] += 1
        s['gen'] += money(r['GEN_FUND']) or 0
        s['gr'] += money(r['GRNTS_REVOLV']) or 0
        s['tot'] += money(r['TOT_EXP']) or 0
        if r['IN_OUT_DIST'] != 'Out-of-District' and r['FUNC_CAT_CODE'] not in (
                'OODD', OUT_TRANSPORT, OUT_TUITION):
            s['pp'].append(money(r['PER_PUPIL_EXP']) or 0)
            if r['DIST_CODE'] == LUNENBURG:
                s['lun'] = money(r['PER_PUPIL_EXP'])

    out2 = io.StringIO()
    w2 = csv.DictWriter(out2, fieldnames=STATE_FIELDS, lineterminator='\n')
    w2.writeheader()
    n_state = 0
    for k in sorted(st):
        fy, level, cat, code = k
        s = st[k]
        pp = sorted(s['pp'])
        basis = ('per pupil, in-district FTE' if pp else
                 'not published — DESE prints 0 per pupil against out-of-district rows')
        rank = ''
        if pp and s['lun'] is not None:
            rank = '%d of %d' % (sum(1 for v in pp if v > s['lun']) + 1, len(pp))
        w2.writerow(dict(
            fy=fy, level=level, func_cat_code=cat, func_code=code, func_desc=s['desc'],
            districts=s['n'], gen_fund_total=s['gen'], grants_revolving_total=s['gr'],
            total=s['tot'],
            grant_share=('%.4f' % (s['gr'] / s['tot'])) if s['tot'] else '',
            per_pupil_basis=basis,
            per_pupil_min=pp[0] if pp else '',
            per_pupil_p25=('%.1f' % quantile(pp, 0.25)) if pp else '',
            per_pupil_median=('%.1f' % statistics.median(pp)) if pp else '',
            per_pupil_p75=('%.1f' % quantile(pp, 0.75)) if pp else '',
            per_pupil_max=pp[-1] if pp else '',
            lunenburg_per_pupil='' if s['lun'] is None else s['lun'],
            lunenburg_rank_of_districts=rank, doc_id=DOC))
        n_state += 1
    return out.getvalue(), out2.getvalue(), all_fails, checked, n_rows, n_state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if either output no longer reproduces')
    a = ap.parse_args()

    if not os.path.exists(SRC):
        print('%s is catalogued but not on disk.\nrun: python3 scripts/sync_archive.py '
              '--pull' % DOC)
        return 1
    keep = peers()
    rows = read_workbook()
    print('%s\n  %s rows, %d districts, SY%s-SY%s'
          % (DOC, f'{len(rows):,}', len({r['DIST_CODE'] for r in rows}),
             min(r['SY'] for r in rows), max(r['SY'] for r in rows)))

    try:
        text, state, fails, checked, n_rows, n_state = build(rows, keep)
    except ValueError as e:
        print('\nA row could not be classified: %s' % e)
        print('Nothing written. A row whose level is unknown cannot be aggregated, and a\n'
              'silent double count is the failure this extract exists to prevent.')
        return 1

    levels = {}
    for r in rows:
        levels[r['_level']] = levels.get(r['_level'], 0) + 1
    print('  levels: ' + ', '.join('%s %s' % (k, f'{v:,}')
                                   for k, v in sorted(levels.items())))
    print('  %d district-years, every identity asserted' % checked)
    if fails:
        print('\n%d identity failure(s):' % len(fails))
        for (sy, lea), label, d in fails[:20]:
            print('  SY%s %s  %s  off by $%s' % (sy, lea, label, f'{d:,}'))
        print('\nNothing written. The hierarchy this extract asserts no longer holds, and\n'
              'an unverified hierarchy is exactly what produces a plausible double count.')
        return 1

    (pp_ok, pp_bad), (fte_ok, fte_bad) = cross_check(rows, keep)
    print('  per-pupil vs dese-radar.csv (RADAR workbook): %d agree, %d disagree'
          % (pp_ok, len(pp_bad)))
    print('  TOT_EXP / FTE pupils == PER_PUPIL_EXP:        %d agree, %d disagree'
          % (fte_ok, len(fte_bad)))
    if not pp_ok or not fte_ok:
        print('\nA cross-check matched NOTHING, which looks exactly like data that is\n'
              'absent. Nothing written.')
        return 1
    if pp_bad or fte_bad:
        for b in (pp_bad + fte_bad)[:10]:
            print('    %s' % (b,))
        print('\nThis dataset disagrees with the RADAR workbook already in the archive.\n'
              'That is a finding about two DESE publications, not something to smooth.\n'
              'Nothing written.')
        return 1

    if a.check:
        bad = []
        for path, want in ((OUT_ROWS, text), (OUT_STATE, state)):
            have = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
            if have != want:
                bad.append(os.path.relpath(path, ROOT))
        if bad:
            print('\nstale: %s\nRe-run: python3 scripts/extract_dese_finance.py'
                  % ', '.join(bad))
            return 1
        print('\nok: both extracts still reproduce')
        return 0

    open(OUT_ROWS, 'w', encoding='utf-8', newline='').write(text)
    open(OUT_STATE, 'w', encoding='utf-8', newline='').write(state)
    print('\nwrote %s  %s rows (%d districts)'
          % (os.path.relpath(OUT_ROWS, ROOT), f'{n_rows:,}', len(keep)))
    print('wrote %s  %s rows (every district, as a distribution)'
          % (os.path.relpath(OUT_STATE, ROOT), f'{n_state:,}'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
