#!/usr/bin/env python3
"""New growth, total valuation and the tax rate, FY1986-FY2010, read from the annual town
reports and PROVED row by row.

    python3 scripts/extract_new_growth_history.py           # writes the CSV
    python3 scripts/extract_new_growth_history.py --check   # fails if the CSV would change

Writes `sources/data/report-new-growth-history.csv`, ONE ROW PER PRINTING (`fy` is the
fiscal year the figures are about; `edition` is the report they were printed in): a fiscal year
printed in five editions is five rows, each with its edition, its line numbers in
`sources/town-annual-reports/text/` and the raw printed tokens. Disagreeing printings are
recorded side by side and flagged; nothing is averaged or picked (rule 13a).

The tables, located by their own printed headings, columns named from headers READ and
written down below (rule 13b, never inferred):

| printed_table | editions | columns as printed |
|---|---|---|
| `new_growth` | 1998-2010 | Fiscal Year, (No. of New Structures), Added/New Growth Valuation, (Prior) Tax Rate, New (Growth) Revenues, Change |
| `valuation_history` | 1998-2010 | Fiscal Year, Tax Rate, Total Valuation, Accounts, Tax Levy / Taxes Raised, Change |
| `property_valuations` | 1995-1997 | two fiscal years side by side: real estate, personal property, total, rate, taxes, class table |
| `levy_history` | 1995-1997 | Previous Years Assessment and Tax Levy History: Fiscal Year, Rate, Valuation, Taxes Raised |
| `town_data_page` | 1990-2000 | the front-matter `TAX RATE: $x (Fiscal YYYY)` line |
| `tax_collector` | 1985 | the FY86 Proposition 2 1/2 increase: allowable 2 1/2, new growth, debt exemption, TOTAL |

What proves each row (its `status`):

* `new_growth`: printed valuation x printed rate / 1000 = printed revenue. Revenue is printed
  in whole dollars, so the computed figure must ROUND to it; within $1 otherwise is labelled
  `within $1 rounding tolerance` (notes/process/TOLERANCES.md).
* `valuation_history`, `levy_history`: valuation x rate / 1000 = levy, to the cent.
* `property_valuations`: real estate + personal property = total; the five classes = TOTAL
  VALUATION (valuation and accounts); real-estate tax + personal-property tax = total
  levied; total x rate / 1000 = total levied.
* `tax_collector`: the three items = the printed TOTAL.
* `town_data_page`: nothing on the page tests it -> `no check` (cross-checks still recorded).

A row whose identity fails is REFUSED unless its failing figures are corroborated as READ
correctly -- the same figures printed in another edition, or the state's file -- in which
case it is written `check failed`: the town's arithmetic disagrees, not our reading.

Cross-checks, per row, in `cross_edition` and `cross_state`:
* every other printing of the same fiscal year and field;
* the state (DLS) files: dls-new-growth.csv (FY2003+), dls-assessed-values.csv (FY2002+),
  dls-tax-rates.csv residential (FY2003+), and dls-avg-tax-bill.csv (FY1988+) where
  avg_sf_value x rate / 1000 must round to the whole-dollar avg_sf_bill.
"""
import csv
import io
import re
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / 'sources' / 'town-annual-reports' / 'text'
DATA = ROOT / 'sources' / 'data'
OUT = DATA / 'report-new-growth-history.csv'
TOLERANCE_PHRASE = 'within $1 rounding tolerance'   # notes/process/TOLERANCES.md; never reword
DOR = '162'   # Lunenburg's DOR code in the DLS files

# ---- layouts, read off each page and written down (rule 13b) -------------------------
NG5 = ['structures', 'valuation', 'rate', 'revenue', 'change']
NG4 = ['valuation', 'rate', 'revenue', 'change']
VH = ['rate', 'valuation', 'accounts', 'levy', 'change']


def yrs(a, b):
    return list(range(a, b - 1, -1))


NEW_GROWTH = {   # file stem -> (heading regex, columns, fiscal years printed, top to bottom)
    '4524-1998-annual-town-report': (r'^New Growth Revenue History$', NG5, yrs(1998, 1994)),
    '4616-1999-annual-town-report': (r'^New Growth Revenue History$', NG5, yrs(1999, 1995)),
    '4526-2000-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2000, 1995)),
    '4527-2001-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2001, 1995)),
    '4528-2002-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2002, 1995)),
    '4529-2003-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2003, 1995)),
    '4530-2004-annual-town-report': (r'^New Growth Revenue-$', NG4, yrs(2004, 1996)),
    '4513-2005-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2005, 2000)),
    '4514-2006-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2006, 2000)),
    '4515-2007-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2007, 2000)),
    '4516-2008-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2008, 2001)),
    '4517-2009-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2009, 2002)),
    '4518-2010-annual-town-report': (r'^New Growth Revenue$', NG4, yrs(2010, 2002)),
}
VAL_HISTORY = {
    '4524-1998-annual-town-report': yrs(1998, 1994),
    '4616-1999-annual-town-report': yrs(1999, 1995),
    '4526-2000-annual-town-report': yrs(1999, 1995),   # the FY2000 edition prints no FY2000 row
    '4527-2001-annual-town-report': yrs(2001, 1996),
    '4528-2002-annual-town-report': yrs(2002, 1997),
    '4529-2003-annual-town-report': yrs(2003, 1998),
    '4530-2004-annual-town-report': yrs(2004, 1999),
    '4513-2005-annual-town-report': yrs(2005, 2000),
    '4514-2006-annual-town-report': yrs(2006, 2001),
    '4515-2007-annual-town-report': yrs(2007, 2002),
    '4516-2008-annual-town-report': yrs(2008, 2003),
    '4517-2009-annual-town-report': yrs(2009, 2004),
    '4518-2010-annual-town-report': yrs(2010, 2005),
}
PROPERTY_VALUATIONS = {   # file stem -> (two years side by side, levy-history years)
    '4521-1995-annual-town-report': ((1994, 1995), yrs(1993, 1990)),
    '4522-1996-annual-town-report': ((1995, 1996), yrs(1994, 1990)),
    '4615-1997-annual-town-report': ((1996, 1997), yrs(1995, 1991)),
}
TOWN_DATA = ['4489-1990', '4490-1991', '4491-1992', '4519-1993', '4520-1994', '4521-1995',
             '4522-1996', '4615-1997', '4524-1998', '4616-1999', '4526-2000']
TAX_COLLECTOR = ('4485-1985-annual-town-report', 1986)

FIELDS = ['new_structures', 'ng_added_valuation', 'ng_rate', 'ng_revenue',
          'total_valuation', 'tax_rate', 'accounts', 'tax_levy']
COLUMNS = ['fy', 'printed_table', 'edition', 'edition_file', 'lines', 'raw'] + FIELDS + [
    'status', 'reconciliation', 'cross_edition', 'cross_state']

# ---- tokens ------------------------------------------------------------------------------
NUM = re.compile(r'^-?[\d,]+(\.\d+)?$')
SEP_AS_STOP = re.compile(r'^\d{1,3}\.\d{3},\d{3}$')   # '9.983,300': a comma scanned as a stop
CHANGE = re.compile(r'^(-|-0-|-?\d+[.,]\d+%?)$')
SPLIT_MINUS_PCT = re.compile(r'(^|\s)- (\d+[.,]\d+%)')


def tokens(path):
    """Every whitespace token with its 1-based line number; lone '$' dropped."""
    out, lines = [], path.read_text(encoding='utf-8', errors='replace').splitlines()
    for n, line in enumerate(lines, 1):
        # A PERCENTAGE WHOSE MINUS SIGN TEXTRACT SPACED OFF: `- 100.0000%` in the 1999 rescan
        # (View/4616), `-100.0000%` in the first scan. Split, the `-` reads as a nil column
        line = SPLIT_MINUS_PCT.sub(r'\1-\2', line)
        for t in line.split():
            t = t.lstrip('$')
            if t:
                out.append((t, n))
    return out, lines


def num(tok, repairs):
    """Decimal from a printed token; None for a printed dash. Records any repair."""
    if tok in ('-', '-0-'):
        return None
    t = tok.rstrip('.') if re.match(r'^[\d,]+\.$', tok) else tok
    if SEP_AS_STOP.match(t):
        repairs.append(f"'{tok}' read as {t.replace('.', ',')} (a separator scanned as a full stop)")
        t = t.replace('.', ',')
    if not NUM.match(t):
        raise ValueError(f'not a number: {tok!r}')
    return Decimal(t.replace(',', ''))


def money(d, places='1'):
    return d.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def fmt(d):
    if d is None:
        return ''
    s = format(d.normalize(), 'f') if d == d.to_integral() else format(d, 'f')
    return s


def find(toks, pattern, start=0, lines=None):
    """Index of the first token on the first line matching `pattern` (whole line)."""
    rx = re.compile(pattern)
    for i in range(start, len(toks)):
        n = toks[i][1]
        if rx.match(lines[n - 1].strip()) and (i == 0 or toks[i - 1][1] != n):
            return i
    raise SystemExit(f'heading {pattern!r} not found')


def read_rows(toks, i, cols, years, where):
    """Rows of a year-led table from token i. Refuses if a declared year is not where the
    layout says. Returns [(year, {col: token}, [tokens], (first line, last line))]."""
    while toks[i][0] != str(years[0]):
        i += 1
    rows = []
    required = [c for c in cols if c != 'change']
    for k, y in enumerate(years):
        if toks[i][0] != str(y):
            raise SystemExit(f'{where}: expected FY{y} at line {toks[i][1]}, found {toks[i][0]!r}')
        got, used = {}, [toks[i]]
        i += 1
        for c in required:
            got[c] = toks[i][0]
            used.append(toks[i])
            i += 1
        nxt = str(years[k + 1]) if k + 1 < len(years) else None
        if 'change' in cols and i < len(toks) and toks[i][0] != nxt and CHANGE.match(toks[i][0]):
            got['change'] = toks[i][0]
            used.append(toks[i])
            i += 1
        rows.append((y, got, used, (used[0][1], used[-1][1])))
    return rows


def blank_row(fy, table, stem, span, used):
    return {'fiscal_year': fy, 'table': table, 'edition': stem.split('-')[1],
            'edition_file': stem + '.txt',
            'lines': f'{span[0]}' if span[0] == span[1] else f'{span[0]}-{span[1]}',
            'raw': ' | '.join(t for t, _ in used), **{f: None for f in FIELDS},
            'checks': [], 'repairs': []}


def close(computed, printed, unit):
    """(ok, text). unit='dollar': printed whole dollars, computed must round to it.
    unit='cent': to the cent. Either: within $1 -> tolerance label."""
    target = money(computed) if unit == 'dollar' else money(computed, '0.01')
    diff = printed - target
    if diff == 0:
        how = 'rounds to' if computed != target else 'equals'
        return True, f'{fmt(computed)} {how} printed {fmt(printed)}'
    if abs(printed - computed) <= 1:
        return True, (f'{fmt(computed)} vs printed {fmt(printed)}: {TOLERANCE_PHRASE} '
                      f'(printed differs by ${fmt(abs(printed - computed).quantize(Decimal("0.01")))})')
    return False, f'{fmt(computed)} vs printed {fmt(printed)}: off by {fmt(printed - target)}'


# ---- readers -----------------------------------------------------------------------------
def read_new_growth(stem):
    pattern, cols, years = NEW_GROWTH[stem]
    toks, lines = tokens(TEXT / f'{stem}.txt')
    i = find(toks, pattern, lines=lines)
    out = []
    for y, got, used, span in read_rows(toks, i, cols, years, stem):
        r = blank_row(y, 'new_growth', stem, span, used)
        rep = r['repairs']
        if 'structures' in got:
            r['new_structures'] = num(got['structures'], rep)
        r['ng_added_valuation'] = num(got['valuation'], rep)
        r['ng_rate'] = num(got['rate'], rep)
        r['ng_revenue'] = num(got['revenue'], rep)
        if None not in (r['ng_added_valuation'], r['ng_rate'], r['ng_revenue']):
            ok, txt = close(r['ng_added_valuation'] * r['ng_rate'] / 1000, r['ng_revenue'], 'dollar')
            r['checks'].append((ok, 'valuation x rate / 1000: ' + txt))
        else:
            r['nocheck'] = 'valuation, rate and revenue printed as dashes'
        out.append(r)
    return out


def read_val_history(stem):
    toks, lines = tokens(TEXT / f'{stem}.txt')
    i = find(toks, r'^Valuation and Tax History$', lines=lines)
    out = []
    for y, got, used, span in read_rows(toks, i, VH, VAL_HISTORY[stem], stem):
        r = blank_row(y, 'valuation_history', stem, span, used)
        rep = r['repairs']
        r['tax_rate'] = num(got['rate'], rep)
        r['total_valuation'] = num(got['valuation'], rep)
        r['accounts'] = num(got['accounts'], rep)
        r['tax_levy'] = num(got['levy'], rep)
        ok, txt = close(r['total_valuation'] * r['tax_rate'] / 1000, r['tax_levy'], 'cent')
        r['checks'].append((ok, 'valuation x rate / 1000: ' + txt))
        out.append(r)
    return out


def values_after(toks, i, n):
    """n numeric tokens following the label line that token i starts."""
    line = toks[i][1]
    j = i
    while toks[j][1] == line:
        j += 1
    vals = []
    while len(vals) < n:
        t, ln = toks[j]
        if not NUM.match(t.rstrip('.')):
            raise SystemExit(f'expected a figure at line {ln}, found {t!r}')
        vals.append(toks[j])
        j += 1
    return vals, j


def read_property_valuations(stem):
    (y0, y1), hist_years = PROPERTY_VALUATIONS[stem]
    toks, lines = tokens(TEXT / f'{stem}.txt')
    a = find(toks, r'^Property Valuations$', lines=lines)
    hdr = lines[toks[a][1]] + ' ' + lines[toks[a][1] + 1]   # the two lines after the heading
    if f'Fiscal {y0}' not in hdr or f'Fiscal {y1}' not in hdr:
        raise SystemExit(f'{stem}: Property Valuations header is not Fiscal {y0} / Fiscal {y1}: {hdr!r}')
    got, used_all = {}, []
    pos = a
    for key, label, n in [
            ('re', r'^Taxable Real Estate$', 2), ('pp', r'^Taxable Personal Property$', 2),
            ('total', r'^Total Assessed Valuation$', 2),
            ('rate', r'^Tax Rate \(per \$1,000 of valuation\)$', 2),
            ('re_tax', r'^Taxable Real Estate$', 2), ('pp_tax', r'^Taxable Personal Property$', 2),
            ('levy', r'^Total Taxes Levied$', 2),
            ('res', r'^Residential$', 4), ('os', r'^Open Space$', 4), ('com', r'^Commercial$', 4),
            ('ind', r'^Industrial$', 4), ('ppc', r'^Personal Property$', 4),
            ('tot', r'^TOTAL VALUATION$', 4)]:
        pos = find(toks, label, pos + 1, lines)
        vals, pos = values_after(toks, pos, n)
        pos -= 1
        got[key] = vals
        used_all.append((key, vals))
    out = []
    for k, y in enumerate((y0, y1)):
        rep = []
        g = {key: num(v[k][0], rep) for key, v in got.items() if len(v) == 2}
        cls = {key: (num(v[2 * k][0], rep), num(v[2 * k + 1][0], rep))
               for key, v in got.items() if len(v) == 4}
        used = [v[k] for _, v in used_all if len(v) == 2] + \
               [t for _, v in used_all if len(v) == 4 for t in v[2 * k:2 * k + 2]]
        lns = sorted(n for _, n in used)
        r = blank_row(y, 'property_valuations', stem, (lns[0], lns[-1]), [])
        r['raw'] = ' | '.join(f'{key}={" ".join(t for t, _ in (v[k:k + 1] if len(v) == 2 else v[2 * k:2 * k + 2]))}'
                              for key, v in used_all)
        r['repairs'] = rep
        r['total_valuation'], r['tax_rate'], r['tax_levy'] = g['total'], g['rate'], g['levy']
        r['accounts'] = cls['tot'][0]
        c = r['checks']
        c.append((g['re'] + g['pp'] == g['total'],
                  f"real estate + personal property = {fmt(g['re'] + g['pp'])} vs total {fmt(g['total'])}"))
        sv = sum(cls[x][1] for x in ('res', 'os', 'com', 'ind', 'ppc'))
        sa = sum(cls[x][0] for x in ('res', 'os', 'com', 'ind', 'ppc'))
        c.append((sv == cls['tot'][1] == g['total'],
                  f"five classes = {fmt(sv)} vs TOTAL VALUATION {fmt(cls['tot'][1])}"))
        c.append((sa == cls['tot'][0], f"class accounts = {fmt(sa)} vs {fmt(cls['tot'][0])}"))
        c.append((g['re_tax'] + g['pp_tax'] == g['levy'],
                  f"real-estate tax + personal-property tax = {fmt(g['re_tax'] + g['pp_tax'])} vs total levied {fmt(g['levy'])}"))
        ok, txt = close(g['total'] * g['rate'] / 1000, g['levy'], 'cent')
        c.append((ok, 'valuation x rate / 1000: ' + txt))
        out.append(r)
    h = find(toks, r'^Previous Years Assessment and Tax Levy History$', pos, lines)
    for y, gotr, used, span in read_rows(toks, h, ['rate', 'valuation', 'levy'], hist_years, stem):
        r = blank_row(y, 'levy_history', stem, span, used)
        rep = r['repairs']
        r['tax_rate'] = num(gotr['rate'], rep)
        r['total_valuation'] = num(gotr['valuation'], rep)
        r['tax_levy'] = num(gotr['levy'], rep)
        ok, txt = close(r['total_valuation'] * r['tax_rate'] / 1000, r['tax_levy'], 'cent')
        r['checks'].append((ok, 'valuation x rate / 1000: ' + txt))
        out.append(r)
    return out


def read_town_data(prefix):
    path = next(TEXT.glob(f'{prefix}-*.txt'))
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    rx = re.compile(r'^\$\s*([\d.]+)\s*\(Fiscal (\d{4})\)$')
    for n, line in enumerate(lines, 1):
        if line.strip() == 'TAX RATE:':
            m = rx.match(lines[n].strip())
            if not m:
                raise SystemExit(f'{path.name}:{n + 1}: TAX RATE line not as declared: {lines[n]!r}')
            r = blank_row(int(m.group(2)), 'town_data_page', path.stem, (n, n + 1), [])
            r['raw'] = f'TAX RATE: | {lines[n].strip()}'
            r['tax_rate'] = Decimal(m.group(1))
            r['nocheck'] = 'the front-matter page prints the rate alone; nothing on it tests it'
            return [r]
    raise SystemExit(f'{path.name}: no TAX RATE: line')


def read_tax_collector():
    stem, fy = TAX_COLLECTOR
    toks, lines = tokens(TEXT / f'{stem}.txt')
    a = find(toks, r'^Under the provisions of Proposition 2½, the town voted to increase taxes for FY 86 as follows:$', lines=lines)
    vals = {}
    used = []
    pos = a
    for key, label in [('allow', r'^Allowable 2½ increase$'), ('ng', r'^Allowable new growth$'),
                       ('debt', r'^Fire truck debt exemption$'), ('total', r'^TOTAL$')]:
        pos = find(toks, label, pos + 1, lines)
        v, pos = values_after(toks, pos, 1)
        pos -= 1
        vals[key] = v[0]
        used.append((key, v[0]))
    lns = [n for _, (_, n) in used]
    r = blank_row(fy, 'tax_collector', stem, (min(lns) - 1, max(lns)), [])
    r['raw'] = ' | '.join(f'{k}={t}' for k, (t, _) in used)
    rep = r['repairs']
    d = {k: num(t, rep) for k, (t, _) in vals.items()}
    r['ng_revenue'] = d['ng']
    s = d['allow'] + d['ng'] + d['debt']
    r['checks'].append((s == d['total'],
                        f"2 1/2 increase + new growth + debt exemption = {fmt(s)} vs TOTAL {fmt(d['total'])}"))
    r['note_extra'] = 'revenue only: no added valuation or rate printed, so the new growth identity cannot be tested'
    return [r]


# ---- cross-checks ------------------------------------------------------------------------
def load_dls():
    def rows(name):
        with open(DATA / name, newline='') as f:
            return {int(r['fy']): r for r in csv.DictReader(f) if r['dor_code'] == DOR and r['fy']}
    return {k: rows(f'dls-{k}.csv') for k in ('new-growth', 'assessed-values', 'tax-rates', 'avg-tax-bill')}


def D(s):
    return Decimal(s) if s not in ('', None) else None


def cross_state(r, dls):
    fy, notes = r['fiscal_year'], []
    ng = dls['new-growth'].get(fy)
    if r['ng_revenue'] is not None and ng and ng['total_levy']:
        for f, col in (('ng_added_valuation', 'total_value'), ('ng_revenue', 'total_levy')):
            if r[f] is None:
                continue
            s = D(ng[col])
            notes.append(f"DLS new growth {col} {fmt(s)}: " +
                         ('agrees' if s == r[f] else f'DISAGREES (town {fmt(r[f])}, diff {fmt(r[f] - s)})'))
    av = dls['assessed-values'].get(fy)
    if r['total_valuation'] is not None and av and av['total']:
        s = D(av['total'])
        notes.append(f'DLS assessed total {fmt(s)}: ' +
                     ('agrees' if s == r['total_valuation'] else f"DISAGREES (diff {fmt(r['total_valuation'] - s)})"))
    if r['tax_rate'] is not None:
        tr = dls['tax-rates'].get(fy)
        if tr and tr['residential']:
            s = D(tr['residential'])
            notes.append(f'DLS residential rate {fmt(s)}: ' +
                         ('agrees' if s == r['tax_rate'] else 'DISAGREES'))
        ab = dls['avg-tax-bill'].get(fy)
        if ab and ab['avg_sf_value'] and ab['avg_sf_bill'] and D(ab['avg_sf_bill']) > 0:
            v, b = D(ab['avg_sf_value']), D(ab['avg_sf_bill'])
            c = v * r['tax_rate'] / 1000
            notes.append(f'DLS avg single-family {fmt(v)} x {fmt(r["tax_rate"])} / 1000 = {fmt(money(c, "0.01"))}, bill {fmt(b)}: ' +
                         ('agrees (rounds to the bill)' if money(c) == b else 'DISAGREES'))
        elif ab:
            notes.append('DLS avg tax bill prints no bill for this year: no check')
    return '; '.join(notes)


def cross_edition(rows):
    by = defaultdict(list)
    for r in rows:
        for f in FIELDS:
            if r[f] is not None:
                by[(r['fiscal_year'], f)].append(r)
    for r in rows:
        notes = []
        for f in FIELDS:
            if r[f] is None:
                continue
            others = [o for o in by[(r['fiscal_year'], f)] if o is not r]
            if not others:
                continue
            same = sorted({f"{o['edition']} {o['table']}" for o in others if o[f] == r[f]})
            diff = sorted({f"{o['edition']} {o['table']} {fmt(o[f])}" for o in others if o[f] != r[f]})
            if diff:
                notes.append(f'{f}: DISAGREES with ' + ', '.join(diff) +
                             (f' (agrees with {len(same)})' if same else ''))
            else:
                notes.append(f'{f}: agrees with {len(same)} other printing(s)')
        r['cross_edition'] = '; '.join(notes)


def corroborated(r, rows, dls):
    """For a row whose identity fails: are its printed figures READ correctly? True when the
    same valuation and revenue are printed in another edition, or the revenue is the state's."""
    fy = r['fiscal_year']
    if r['table'] == 'new_growth':
        twin = [o for o in rows if o is not r and o['table'] == 'new_growth' and o['fiscal_year'] == fy
                and o['ng_added_valuation'] == r['ng_added_valuation'] and o['ng_revenue'] == r['ng_revenue']]
        if twin:
            return f"valuation and revenue printed identically in {', '.join(sorted({o['edition'] for o in twin}))}"
    return None


def prior_rate_note(r, rows):
    """For a new growth row: does the identity close at the PRIOR fiscal year's rate as the
    valuation tables print it? Reported whatever the printed rate column said."""
    prior = sorted({o['tax_rate'] for o in rows if o['fiscal_year'] == r['fiscal_year'] - 1
                    and o['table'] in ('valuation_history', 'property_valuations', 'levy_history')
                    and o['tax_rate'] is not None})
    if len(prior) != 1 or r['ng_added_valuation'] is None:
        return None
    p = prior[0]
    ok, txt = close(r['ng_added_valuation'] * p / 1000, r['ng_revenue'], 'dollar')
    tag = 'printed rate IS the prior year rate' if p == r['ng_rate'] else \
        f"printed rate {fmt(r['ng_rate'])} is NOT FY{r['fiscal_year'] - 1}'s rate {fmt(p)}"
    return f"{tag}; at FY{r['fiscal_year'] - 1}'s {fmt(p)}: " + ('closes, ' if ok else 'fails, ') + txt


def build():
    rows = []
    for stem in NEW_GROWTH:
        rows += read_new_growth(stem)
    for stem in VAL_HISTORY:
        rows += read_val_history(stem)
    for stem in PROPERTY_VALUATIONS:
        rows += read_property_valuations(stem)
    for p in TOWN_DATA:
        rows += read_town_data(p)
    rows += read_tax_collector()
    dls = load_dls()
    cross_edition(rows)
    refused = []
    for r in rows:
        r['cross_state'] = cross_state(r, dls)
        notes = [t for _, t in r['checks']]
        if r['table'] == 'new_growth' and r['ng_rate'] is not None:
            p = prior_rate_note(r, rows)
            if p:
                notes.append(p)
        notes += r['repairs'] and ['repair: ' + x for x in r['repairs']] or []
        if r.get('note_extra'):
            notes.append(r['note_extra'])
        if not r['checks']:
            r['status'] = 'no check'
            notes.insert(0, r.get('nocheck', 'no identity printed'))
        elif all(ok for ok, _ in r['checks']):
            r['status'] = 'checked'
        else:
            why = corroborated(r, rows, dls)
            if not why and r['table'] == 'new_growth' and 'DLS new growth total_levy' in r['cross_state'] \
                    and 'total_levy {}: agrees'.format(fmt(r['ng_revenue'])) in r['cross_state']:
                why = 'revenue agrees with the state file'
            if not why:
                refused.append(f"FY{r['fiscal_year']} {r['table']} {r['edition_file']}:{r['lines']}: " + '; '.join(notes))
                continue
            r['status'] = 'check failed'
            notes.insert(0, f'the town\'s arithmetic fails; figures read correctly ({why})')
        r['reconciliation'] = '; '.join(notes)
    if refused:
        raise SystemExit('REFUSED -- identity fails and the reading is not corroborated:\n  ' + '\n  '.join(refused))
    rows.sort(key=lambda r: (r['fiscal_year'], r['table'], r['edition']))
    return rows


def render(rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(COLUMNS)
    for r in rows:
        r = dict(r, fy=r['fiscal_year'], printed_table=r['table'])
        w.writerow([fmt(r[c]) if isinstance(r[c], Decimal) else r[c] for c in COLUMNS])
    return buf.getvalue()


def main():
    rows = build()
    text = render(rows)
    if '--check' in sys.argv:
        cur = OUT.read_text() if OUT.exists() else ''
        if cur != text:
            sys.exit(f'{OUT.relative_to(ROOT)} is stale: run scripts/extract_new_growth_history.py')
        print(f'{OUT.relative_to(ROOT)}: reproduces ({len(rows)} rows)')
        return
    OUT.write_text(text)
    st = defaultdict(int)
    for r in rows:
        st[r['status']] += 1
    print(f'wrote {OUT.relative_to(ROOT)}: {len(rows)} rows, ' + ', '.join(f'{k} {v}' for k, v in sorted(st.items())))


if __name__ == '__main__':
    main()
