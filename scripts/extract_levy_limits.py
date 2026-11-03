#!/usr/bin/env python3
"""Lunenburg's tax levy, decomposed the way Proposition 2 1/2 builds it, FY1986-FY2026, from the
Division of Local Services' own files.

    python3 scripts/extract_levy_limits.py           # writes sources/data/dls-levy-limits.csv
    python3 scripts/extract_levy_limits.py --check   # fails if the CSV would change

The files are landed by scripts/fetch_dls_levy_limits.py (see its docstring for every address).
One row per fiscal year:

    levy_limit_prior + prop25_increase + new_growth + override  = levy_limit       (identity A)
    levy_limit + debt_exclusion + other_exclusion               = max_levy         (identity B)
    max_levy - tax_levy                                         = excess_capacity  (identity C)
    residential + open space + commercial + industrial + PP     = total_levy_by_class (identity D)

WHAT EACH FIGURE IS, AND WHOSE.
* `levy_limit`, `max_levy`, `tax_levy`, `excess_capacity`: printed, per town per year, in the
  Excess Levy Capacity files (excp8589/excp9099/excp0009 for FY1985-FY2006, the Gateway export
  ExcessLevyAndOverrideCap for FY2007 on). `levy_limit` is the column DLS heads "Levy Limit
  w/o Debt & Capital Exclusions"; `max_levy` is "Maximum Levy Limit".
* `levy_limit_prior`: the previous year's printed `levy_limit`. Cross-checked against the
  new growth files' own printed "Prior Year's Levy Limit" wherever one exists.
* `prop25_increase`: OUR ARITHMETIC -- 2.5% of the prior limit, rounded half up to the dollar.
  The statute's formula; DLS does not publish the line. Written only when identity A closes.
* `new_growth`: printed, "Total New Growth Applied to the Limit" (Grow9299, grow0009 for
  FY1992-FY2002; the Gateway new growth export, via dls-new-growth.csv, for FY2003 on). NO file
  in either publication carries new growth before FY1992, so A cannot be tested before then.
* `override`: winning overrides less winning underrides for the fiscal year, from DLS's
  override votes (dls-override-votes.csv, read from OverrideUnderrideVotes.xlsx).
* `debt_exclusion`: the sum of "Net Excludable Debt" for the fiscal year excluded (DebtEx.xls
  for FY1989-FY2001; the Gateway DebtExcLevyAmt export for FY2002 on).
* `other_exclusion`: winning capital exclusion amounts for the fiscal year (Gateway
  CapitalExclusionVotes, FY1988 on; the retired capital.xls is a cross-check). Lunenburg has
  none in either file, so this is 0 wherever B was tested -- and B closing is what shows that
  nothing else sits between the limit and the maximum levy.
* `residential_levy`, `total_levy_by_class`: printed, Tax Levies by Class (lvcl8689/9099/0009
  for FY1986-FY2002, the Gateway Taxlevybyclass export for FY2003 on).

WHAT IS REFUSED. A and B are cross-document: their parts come from different DLS files. They
must close EXACTLY (TOLERANCES.md: never a tolerance across documents). When one does not, its
parts are not written -- A blanks prop25_increase, new_growth and override and records the
residual in `components_residual`; B blanks debt_exclusion and other_exclusion -- while the
printed figures of that year, which close their own identities, stay. C and D are a row's own
printed identity in one report and close within $1, labelled `within $1 rounding tolerance`.
A row that fails C is not written at all. A class split that fails D is blanked.

Cross-checks, recorded in `checks` and never gating: the printed prior limit in the new growth
file; overlapping years between the retired and current files; the class total against the
tax levy (two reports, which differ by a few dollars in some retired-file years).

A missing figure is never written as zero: a year a file does not cover is left blank and the
`checks` column names which file was looked in.
"""
import argparse
import csv
import hashlib
import io
import os
import sys
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from fetch_dls_tax_bills import newest_export  # noqa: E402

DIR = os.path.join(ROOT, 'sources', 'state-dls')
DATA = os.path.join(ROOT, 'sources', 'data')
OUT = os.path.join(DATA, 'dls-levy-limits.csv')
DOR = 162
FIRST_FY, LAST_FY = 1986, 2026
TOLERANCE_PHRASE = 'within $1 rounding tolerance'   # notes/process/TOLERANCES.md; never reword
ONE = Decimal(1)

COLS = ['fy', 'levy_limit_prior', 'prop25_increase', 'new_growth', 'override', 'levy_limit',
        'debt_exclusion', 'other_exclusion', 'max_levy', 'tax_levy', 'excess_capacity',
        'residential_levy', 'total_levy_by_class', 'components_residual', 'status', 'checks',
        'source_file', 'sha256']

# ---- headers, read off each file and written down (rule 13b) ---------------------------
H_EXCP_OLD = ['Municipality', 'DOR Code', 'FY', 'Levy Limit without Debt & Capital Exclusions',
              'Maximum Levy Limit', 'Total Tax Levy', 'Excess Capacity']
H_LVCL_OLD = ['Municipality', 'DOR Code', 'FY', 'Residential', 'Open Space', 'Commercial',
              'Industrial', 'Personal Property', 'Total']
H_GROW9299 = ['Municipality', 'DOR Code', 'FY', 'Residential New Growth',
              'Residential Growth Applied to Levy Limit', 'Total New Growth Value',
              'Total New Growth Applied to the Limit', 'Res Value of NG as % of Total NG Value',
              'Total Growth Applied to Limit as a % of PY Levy Limit', "Prior Year's Levy Limit"]
H_GROW0009 = ['Municipality', 'DOR Code', 'FY', 'Residential New Growth',
              'Residential Growth Applied to Levy Limit', 'Total New Growth Value',
              'Total New Growth Applied to the Limit', 'Res Value of NG as % of Total NG Value',
              "Prior Year's Levy Limit"]
H_DEBTEX = ['Municipality', 'DOR Code', 'FY Excluded', 'Net Excludable Debt']
H_CAPITAL_OLD = ['DOR Code', 'Municipality', 'Description', 'Date', 'FY', 'Yes', 'No',
                 'Win /Loss', 'Amount']
H_ELC = ['DOR Code', 'Municipality', 'Fiscal Year', 'Levy Limit w/o Debt & Capital Exclusions',
         'Maximum Levy Limit', 'Total Tax Levy', 'Excess Levy Capacity']
H_CLASS = ['DOR Code', 'Municipality', 'Fiscal Year', 'Residential Levy', 'Open Space Levy',
           'Commercial Levy', 'Industrial Levy', 'Personal Property Levy', 'Total Levy']
H_DEBTAMT = ['DOR Code', 'Municipality', 'Vote Date', 'FY Excluded', 'Vote Description',
             'Yes Vote', 'No Vote', 'Net Excludable Debt']
H_CAPITAL = ['DOR Code', 'Municipality', 'Fiscal Year', 'Vote Date', 'Win / Loss', 'Yes Votes',
             'No Votes', 'Department', 'Description', 'Amount']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dec(v):
    """Decimal from a cell; None for a blank. Floats go through repr so 1586.52 stays 1586.52."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, float):
        v = repr(v)
    return Decimal(str(v).replace(',', '').strip())


def fmt(d):
    if d is None:
        return ''
    d = d.quantize(Decimal('0.01'))
    return str(d.quantize(ONE)) if d == d.to_integral_value() else str(d)


def money(d):
    return ('-' if d < 0 else '') + '${:,.2f}'.format(abs(d)).replace('.00', '')


class Source:
    """One workbook: its rows (header-checked), and its provenance."""

    def __init__(self, path, header, sheets=None):
        self.path, self.name, self.sha = path, os.path.basename(path), sha256(path)
        self.rows = []
        for sheet in self._sheets(sheets):
            hi = next((i for i, r in enumerate(sheet) if 'DOR Code' in [str(c).strip() for c in r]), None)
            if hi is None:
                raise SystemExit('%s: no header row' % self.name)
            head = [str(c).strip() for c in sheet[hi]]
            if head[:len(header)] != header:
                raise SystemExit('%s: the columns moved:\n  %s\n  expected %s' % (self.name, head, header))
            for r in sheet[hi + 1:]:
                r = list(r) + [None] * (len(header) - len(r))
                self.rows.append(dict(zip(header, r[:len(header)])))

    def _sheets(self, which):
        if self.path.endswith('.xlsx'):
            import openpyxl
            wb = openpyxl.load_workbook(self.path, read_only=True)
            return [list(ws.iter_rows(values_only=True)) for ws in wb.worksheets]
        import xlrd
        import xlrd.book
        # lvcl8689.xls carries a defined name that refers to itself ('Graph'), and xlrd refuses
        # the whole workbook while resolving names. No figure is read from a defined name, so
        # name resolution is skipped; the cells are read as stored.
        xlrd.book.Book.names_epilogue = lambda self: None
        with open(os.devnull, 'w') as null:
            book = xlrd.open_workbook(self.path, logfile=null)
        sheets = book.sheets()[1:]   # sheet 0 is DLS's introduction / data definitions
        return [[s.row_values(i) for i in range(s.nrows)] for s in sheets]

    def mine(self):
        """Rows for DOR 162, by code (the retired files print the name on a town's first row only)."""
        out = []
        for r in self.rows:
            code = r.get('DOR Code')
            try:
                code = int(float(code))
            except (TypeError, ValueError):
                continue
            if code == DOR:
                out.append(r)
        return out


def fy_of(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def load():
    p = lambda n: os.path.join(DIR, n)  # noqa: E731
    src = dict(
        excp=[Source(p(n), H_EXCP_OLD) for n in ('excp8589.xls', 'excp9099.xls', 'excp0009.xls')],
        elc=Source(newest_export(DIR, 'ExcessLevyAndOverrideCap', '.xlsx'), H_ELC),
        lvcl=[Source(p(n), H_LVCL_OLD) for n in ('lvcl8689.xls', 'lvcl9099.xls', 'lvcl0009.xls')],
        cls=Source(newest_export(DIR, 'Taxlevybyclass', '.xlsx'), H_CLASS),
        grow=[Source(p('Grow9299.xls'), H_GROW9299), Source(p('grow0009.xls'), H_GROW0009)],
        debtex=Source(p('DebtEx.xls'), H_DEBTEX),
        debtamt=Source(newest_export(DIR, 'DebtExcLevyAmt', '.xlsx'), H_DEBTAMT),
        capital_old=Source(p('capital.xls'), H_CAPITAL_OLD),
        capital=Source(newest_export(DIR, 'CapitalExclusionVotes', '.xlsx'), H_CAPITAL),
    )
    return src


def read_csv(name):
    with open(os.path.join(DATA, name), newline='', encoding='utf-8') as fh:
        return [r for r in csv.DictReader(fh) if r['dor_code'] == str(DOR)]


def build():
    s = load()
    used = {}   # fy -> {file name: sha}

    def use(fy, name, sha):
        used.setdefault(fy, {})[name] = sha

    # -- the levy limit series --------------------------------------------------------
    elc, cross = {}, {}
    for f in s['excp']:
        for r in f.mine():
            fy = fy_of(r['FY'])
            if fy is None or dec(r['Levy Limit without Debt & Capital Exclusions']) is None:
                continue
            elc[fy] = dict(levy_limit=dec(r['Levy Limit without Debt & Capital Exclusions']),
                           max_levy=dec(r['Maximum Levy Limit']), tax_levy=dec(r['Total Tax Levy']),
                           excess_capacity=dec(r['Excess Capacity']), file=f)
    for r in s['elc'].mine():
        fy = fy_of(r['Fiscal Year'])
        if fy is None or dec(r['Levy Limit w/o Debt & Capital Exclusions']) is None:
            continue
        new = dict(levy_limit=dec(r['Levy Limit w/o Debt & Capital Exclusions']),
                   max_levy=dec(r['Maximum Levy Limit']), tax_levy=dec(r['Total Tax Levy']),
                   excess_capacity=dec(r['Excess Levy Capacity']), file=s['elc'])
        if fy in elc:   # retired and current overlap: record, current wins
            old = elc[fy]
            diffs = ['%s %s vs %s' % (k, fmt(old[k]), fmt(new[k])) for k in
                     ('levy_limit', 'max_levy', 'tax_levy') if abs(old[k] - new[k]) >= 1]
            cross.setdefault(fy, []).append(
                '%s agrees with %s on limit, maximum and levy' % (old['file'].name, s['elc'].name) if not diffs
                else '%s differs from %s: %s' % (old['file'].name, s['elc'].name, '; '.join(diffs)))
        elc[fy] = new

    # -- new growth and the printed prior limit ---------------------------------------
    ng, printed_prior = {}, {}
    for f in s['grow']:
        for r in f.mine():
            fy = fy_of(r['FY'])
            if fy is None or dec(r['Total New Growth Applied to the Limit']) is None:
                continue
            ng[fy] = (dec(r['Total New Growth Applied to the Limit']), f.name, f.sha)
            printed_prior[fy] = (dec(r["Prior Year's Levy Limit"]), f.name)
    for r in read_csv('dls-new-growth.csv'):
        fy = int(r['fy'])
        if not r['total_levy']:
            continue
        if fy in ng and Decimal(r['total_levy']) != ng[fy][0]:
            cross.setdefault(fy, []).append('new growth %s in %s vs %s in %s'
                                            % (fmt(ng[fy][0]), ng[fy][1], r['total_levy'], r['source_file']))
        ng[fy] = (Decimal(r['total_levy']), r['source_file'], r['sha256'])
        printed_prior[fy] = (Decimal(r['prior_levy_limit']), r['source_file'])

    # -- overrides ----------------------------------------------------------------------
    ov, ov_src = {}, None
    for r in read_csv('dls-override-votes.csv'):
        ov_src = (r['source_file'], r['sha256'])
        fy = int(r['fy'])
        if r['result'] == 'WIN':
            sign = 1 if r['vote_type'] == 'Override' else -1
            ov[fy] = ov.get(fy, Decimal(0)) + sign * Decimal(r['amount'])
    ov_first = 1990   # the file's first fiscal year for ANY town; Lunenburg's first vote is FY1990

    # -- exclusions -----------------------------------------------------------------------
    debt_old, debt_new = {}, {}
    for r in s['debtex'].mine():
        fy = fy_of(r['FY Excluded'])
        if fy is not None and dec(r['Net Excludable Debt']) is not None:
            debt_old[fy] = debt_old.get(fy, Decimal(0)) + dec(r['Net Excludable Debt'])
    for r in s['debtamt'].mine():
        fy = fy_of(r['FY Excluded'])
        if fy is not None and dec(r['Net Excludable Debt']) is not None:
            debt_new[fy] = debt_new.get(fy, Decimal(0)) + dec(r['Net Excludable Debt'])
    debtex_years = {fy_of(r['FY Excluded']) for r in s['debtex'].rows} - {None}
    for fy in sorted(set(debt_old) & set(debt_new)):
        cross.setdefault(fy, []).append(
            'debt exclusion %s in DebtEx.xls and %s'
            % ('agrees' if debt_old[fy] == debt_new[fy] else 'is %s vs %s' % (fmt(debt_old[fy]), fmt(debt_new[fy])),
               s['debtamt'].name))
    cap = {}
    for r in s['capital'].mine():
        if str(r['Win / Loss']).strip().upper() == 'WIN':
            fy = fy_of(r['Fiscal Year'])
            cap[fy] = cap.get(fy, Decimal(0)) + dec(r['Amount'])
    cap_old = {}
    for r in s['capital_old'].mine():
        if str(r['Win /Loss']).strip().upper() == 'WIN':
            fy = fy_of(r['FY'])
            cap_old[fy] = cap_old.get(fy, Decimal(0)) + dec(r['Amount'])
    if cap_old and any(cap.get(fy) != v for fy, v in cap_old.items()):
        raise SystemExit('capital.xls and %s disagree about Lunenburg capital exclusions: %s vs %s'
                         % (s['capital'].name, cap_old, cap))
    cap_first = min(fy_of(r['Fiscal Year']) for r in s['capital'].rows if fy_of(r['Fiscal Year']))

    # -- levies by class ----------------------------------------------------------------
    classes = {}
    names_old = ['Residential', 'Open Space', 'Commercial', 'Industrial', 'Personal Property', 'Total']
    names_new = ['Residential Levy', 'Open Space Levy', 'Commercial Levy', 'Industrial Levy',
                 'Personal Property Levy', 'Total Levy']
    for f in s['lvcl']:
        for r in f.mine():
            fy = fy_of(r['FY'])
            if fy:
                classes[fy] = ([dec(r[n]) for n in names_old], f)
    for r in s['cls'].mine():
        fy = fy_of(r['Fiscal Year'])
        if fy is None or dec(r['Total Levy']) is None:
            continue
        new = [dec(r[n]) for n in names_new]
        if fy in classes:
            old = classes[fy][0]
            cross.setdefault(fy, []).append(
                'class levies in %s and %s agree within $1' % (classes[fy][1].name, s['cls'].name)
                if all(a is not None and abs(a - b) <= 1 for a, b in zip(old, new))
                else 'class levies in %s and %s differ' % (classes[fy][1].name, s['cls'].name))
        classes[fy] = (new, s['cls'])

    # -- one row per year -------------------------------------------------------------
    out, refused_c = [], []
    for fy in range(FIRST_FY, LAST_FY + 1):
        e = elc.get(fy)
        if not e:
            raise SystemExit('FY%d: no Excess Levy Capacity row for Lunenburg' % fy)
        use(fy, e['file'].name, e['file'].sha)
        checks, row = [], {'fy': fy}
        # C, the row's own printed identity
        d = e['max_levy'] - e['tax_levy'] - e['excess_capacity']
        if d == 0:
            checks.append('C ok')
        elif abs(d) <= 1:
            checks.append('C ok, %s (printed differs by %s)' % (TOLERANCE_PHRASE, money(abs(d))))
        else:
            refused_c.append('FY%d: maximum levy - tax levy misses the printed excess by %s' % (fy, money(d)))
            continue
        row.update(levy_limit=e['levy_limit'], max_levy=e['max_levy'], tax_levy=e['tax_levy'],
                   excess_capacity=e['excess_capacity'])
        tested = refused = 0
        # A, the components
        prior = elc.get(fy - 1, {}).get('levy_limit')
        row['levy_limit_prior'] = prior
        if fy - 1 in elc:
            use(fy, elc[fy - 1]['file'].name, elc[fy - 1]['file'].sha)
        if fy in printed_prior:
            pp, pf = printed_prior[fy]
            checks.append('prior limit %s %s' % ('matches' if pp == prior else 'is printed %s' % fmt(pp), pf))
        if fy not in ng:
            checks.append('A untested: no new growth for FY%d in Grow9299.xls (FY1992-99), grow0009.xls '
                          '(FY2000-09) or the Gateway new growth export (FY2003 on)' % fy)
        elif fy < ov_first:
            checks.append('A untested: the override votes file starts at FY%d' % ov_first)
        else:
            tested += 1
            inc = (prior * Decimal('0.025')).quantize(ONE, rounding=ROUND_HALF_UP)
            o = ov.get(fy, Decimal(0))
            resid = e['levy_limit'] - (prior + inc + ng[fy][0] + o)
            use(fy, ng[fy][1], ng[fy][2])
            if o:
                use(fy, *ov_src)
            if resid == 0:
                row.update(prop25_increase=inc, new_growth=ng[fy][0], override=o)
                checks.append('A ok')
            else:
                refused += 1
                row['components_residual'] = resid
                checks.append('A refused: prior + 2.5%% + new growth %s + override %s misses the levy '
                              'limit by %s, which no DLS file held here itemises'
                              % (fmt(ng[fy][0]), fmt(o), money(resid)))
        # B, the exclusions
        debt = debt_new.get(fy) if fy >= 2002 else debt_old.get(fy)
        dfile = s['debtamt'] if fy >= 2002 else s['debtex']
        if debt is None and fy >= 2002:
            debt = Decimal(0)   # the Gateway file covers every year from FY2002; no row is no exclusion
        if debt is None:
            # A covered year with no Lunenburg row is UNMATCHED, not zero (rule 13c): FY1989 has
            # rows for other towns and none for Lunenburg, while its maximum levy sits
            # above its limit. So it is left untested rather than written as no exclusion.
            checks.append('B untested: DebtEx.xls (FY%d-FY%d) has no Lunenburg row for FY%d'
                          % (min(debtex_years), max(debtex_years), fy))
        if debt is not None:
            if fy < cap_first:
                checks.append('B untested: the capital exclusion votes start at FY%d' % cap_first)
            else:
                tested += 1
                other = cap.get(fy, Decimal(0))
                d = e['max_levy'] - (e['levy_limit'] + debt + other)
                use(fy, dfile.name, dfile.sha)
                use(fy, s['capital'].name, s['capital'].sha)
                if d == 0:
                    row.update(debt_exclusion=debt, other_exclusion=other)
                    checks.append('B ok')
                else:
                    refused += 1
                    checks.append('B refused: limit + debt exclusion %s (%s) + capital exclusion %s misses '
                                  'the maximum levy by %s' % (fmt(debt), dfile.name, fmt(other), money(d)))
        # D, the class split, and E as a cross-check
        if fy in classes:
            vals, cf = classes[fy]
            use(fy, cf.name, cf.sha)
            parts, total = vals[:5], vals[5]
            if any(v is None for v in parts):
                checks.append('D untested: %s prints only the total for FY%d' % (cf.name, fy))
                row['total_levy_by_class'] = total
            else:
                tested += 1
                d = sum(parts) - total
                if abs(d) <= 1:
                    row.update(residential_levy=parts[0], total_levy_by_class=total)
                    checks.append('D ok' if d == 0 else 'D ok, %s (printed differs by %s)'
                                  % (TOLERANCE_PHRASE, money(abs(d))))
                else:
                    refused += 1
                    checks.append('D refused: the five classes miss the printed total by %s' % money(d))
            if total is not None:
                d = total - e['tax_levy']
                checks.append('E: class total equals the tax levy' if d == 0 else
                              'E: class total differs from the tax levy by %s (two reports; recorded, not gating)'
                              % money(d))
        else:
            checks.append('D untested: no levy-by-class row for FY%d' % fy)
        checks += cross.get(fy, [])
        row['status'] = 'checked' if tested == 3 and not refused else 'partial'
        row['checks'] = '; '.join(checks)
        files = used[fy]
        row['source_file'] = ';'.join(sorted(files))
        row['sha256'] = ';'.join(files[k] for k in sorted(files))
        out.append({k: (fmt(v) if isinstance(v, Decimal) else v) for k, v in row.items()})
    if refused_c:
        raise SystemExit('refused (identity C):\n  ' + '\n  '.join(refused_c))
    return out


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in COLS})
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render(build())
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != text:
            print('STALE %s -- run scripts/extract_levy_limits.py' % rel)
            return 1
        print('ok -- %s reproduces' % rel)
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    rows = list(csv.DictReader(io.StringIO(text)))
    print('%s: %d years, %d checked, %d partial' % (rel, len(rows), sum(r['status'] == 'checked' for r in rows),
                                                    sum(r['status'] == 'partial' for r in rows)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
