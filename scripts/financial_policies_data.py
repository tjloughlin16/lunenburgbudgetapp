#!/usr/bin/env python3
"""THE FIGURES BEHIND THE FINANCIAL POLICY PAGES, read from the documents and nothing typed.

One module, so the four topic pages, the markdown report and the verifier read the same
numbers (rule 7d). Every figure here is read from a held document; every POLICY figure (a
percentage or a dollar amount a rule sets) is asserted VERBATIM on the page of the document
that sets it, so a rule quoted on the page is a rule the document prints (rule 13).

  The state's draft   sources/state-dls/Lunenburg_Financial_Policy_Manual_April_2024.pdf
                      (DLS, April 2024; drafted for the Town and not adopted)
  Today's rules       sources/town-supplementary/docs/506-select-board-policies-and-procedures.pdf
                      (Select Board Policies and Procedures, Article III; text copy beside it)
  Free cash           sources/data/free-cash-history-fincom.csv (the Town's fact sheet), asserted
                      equal to the DLS databank export, CertifiedFreeCashBudget351
  Stabilization       the DLS databank export StablPerBudget351, asserted equal to the annual
                      town reports' trust tables (sources/data/stabilization-balances.csv) to the
                      dollar wherever both hold a year; FY2025 read off the FY2025 annual report
                      and the FY2025 audit, which DISAGREE (held as two figures, never one)
  Debt service        the DLS databank export LongTermDebt351
  OPEB                the FY2025 audit's required supplementary schedule (pdf page 78), nine
                      years, every printed identity re-added here
  Capital             sources/data/capital-funding-history.csv (the FY27 capital plan's table)

Peer towns are the eight the project already compares on free cash (fy28/public/data/
free-cash.json, `peers`): no new peer set is chosen here.
"""
import csv
import io
import os
import re
from decimal import Decimal as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')

MANUAL = 'state-dls/Lunenburg_Financial_Policy_Manual_April_2024.pdf'
MANUAL_URL = 'https://www.mass.gov/doc/lunenburg-financial-policy-manual-april-2024/download'
SBPOL = 'town-supplementary/docs/506-select-board-policies-and-procedures.pdf'
SBPOL_TXT = 'town-supplementary/text/506-select-board-policies-and-procedures.txt'
SBPOL_URL = 'https://www.lunenburgma.gov/DocumentCenter/View/506'
AUDIT_TXT = 'town-supplementary/text/4552-fy-2025-audit-report.txt'
AUDIT = 'town-supplementary/docs/4552-fy-2025-audit-report.pdf'
AUDIT_URL = 'https://www.lunenburgma.gov/DocumentCenter/View/4552'
AR25_TXT = 'town-annual-reports/text/4130-fy-2025-annual-town-report.txt'
AR25 = 'town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf'
DLS_STAB = 'state-dls/StablPerBudget351-2026-11-25-3f4c08a6593d.xlsx'
DLS_FC = 'state-dls/CertifiedFreeCashBudget351-2026-11-25-c47c84ed3c38.xlsx'
DLS_DEBT = 'state-dls/LongTermDebt351-2026-11-25-d4884bc8f426.xlsx'
DLS_PAGE = 'https://dls-gw.dor.state.ma.us/reports/rdPage.aspx?rdReport='
LAW = {
    '5B': 'https://malegislature.gov/Laws/GeneralLaws/PartI/TitleVII/Chapter40/Section5B',
    '6': 'https://malegislature.gov/Laws/GeneralLaws/PartI/TitleVII/Chapter40/Section6',
    '32B': 'https://malegislature.gov/Laws/GeneralLaws/PartI/TitleIV/Chapter32B/Section20',
    'gfoa': 'https://www.gfoa.org/materials/fund-balance-guidelines-for-the-general-fund',
}


class DataError(SystemExit):
    pass


def fail(msg):
    raise DataError('financial_policies_data: ' + msg)


def p(rel):
    return os.path.join(SRC, rel)


def norm(s):
    """Whitespace and the PDF's odd spacing ('f ive', '1 0 percent') folded, for a verbatim test."""
    return re.sub(r'\s+', ' ', s).strip()


_MANUAL_PAGES = None


def manual_page(n):
    global _MANUAL_PAGES
    if _MANUAL_PAGES is None:
        import pypdf
        _MANUAL_PAGES = [norm(x.extract_text() or '') for x in pypdf.PdfReader(p(MANUAL)).pages]
    return _MANUAL_PAGES[n - 1]


def on_manual(n, phrase):
    """Assert a phrase is printed on pdf page n of the draft, and return the page number."""
    if norm(phrase) not in manual_page(n):
        fail('the draft does not print %r on pdf page %d' % (phrase, n))
    return n


_SB = None


def sb_section(title_start):
    """Today's rules: the text of one Article III section of the Select Board's manual."""
    global _SB
    if _SB is None:
        _SB = io.open(p(SBPOL_TXT), encoding='utf-8').read()
    i = _SB.find(title_start)
    if i < 0:
        fail('the Select Board manual has no section starting %r' % title_start)
    j = _SB.find('Section 3.0', i + len(title_start))
    return norm(_SB[i:j if j > 0 else None])


def on_sb(section, phrase):
    if norm(phrase) not in sb_section(section):
        fail('today\'s %s does not print %r' % (section, phrase))
    return section


# THE RULES, each with the words that set it. A rule quoted on a page is asserted here first.
TODAY = {
    'fc_order': on_sb('Section 3.03', 'The highest priority use of Free Cash should be to increase the balance of the Stabilization Account if necessary to a level of at least five percent'),
    'fc_opeb': on_sb('Section 3.03', 'at last 10% of the previous fiscal year’s certified General Fund Free Cash for deposit into the OPEB Trust Fund'),
    'stab_min': on_sb('Section 3.04', 'A minimum balance equal to five percent of the current omnibus budget'),
    'stab_cap': on_sb('Section 3.04', 'The total of all funds should not exceed ten percent of the prior years’ omnibus budget'),
    'stab_old_caps': on_sb('Section 3.04', 'may appropriate an amount not to exceed ten percent of the amount raised the preceding fiscal year by taxation'),
    'stab_two_thirds': on_sb('Section 3.04', 'Any appropriation of funds out of any such fund(s) shall be approved by a two thirds vote'),
    'stab_refill': on_sb('Section 3.04', 'ideally a period not to exceed three years'),
    'reserve': on_sb('Section 3.04', 'The Town’s General Reserve Fund balance is currently set at $50,000'),
    'reserve_cap': on_sb('Section 3.04', 'should not exceed one-half of one percent of the current omnibus budget'),
    'opeb': on_sb('Section 3.07', 'At minimum, the Town will request an amount equivalent to at least 10% of certified General Fund Free Cash'),
    'capital': on_sb('Section 3.02', 'Capital Projects (also referred to as capital assets) are any tangible item that costs $20,000'),
    'debt_regular': on_sb('Section 3.01', 'Regular borrowing debt service costs should not exceed four percent of the regular tax levy'),
    'debt_all': on_sb('Section 3.01', 'should not exceed 14 percent of the total tax levy'),
}
DRAFT = {
    'reserves_total': on_manual(28, 'equivalent to 13 to 20 percent of its prior year annual general fund operating budget'),
    'fc_target': on_manual(29, 'free cash certifications equal to f ive to seven percent of the current year annual general fund budget'),
    'fc_keep': on_manual(29, 'Set aside at least 20 percent of the certified free cash amount as the starting balance'),
    'fc_stab': on_manual(29, 'Appropriate at least 1 0 percent to the special purpose stabilization funds and 5 percent to the Town’s general stabilization'),
    'fc_opeb': on_manual(29, 'Appropriate at least 10 percent to the Town’s other postemployment benefits (OPEB) trust fund'),
    'fc_capital': on_manual(29, 'Apply at least 20 percent but no more than 30 percent to the cash capital budget'),
    'fc_other': on_manual(30, 'Use the lesser of 10 percent or $250,000 for noncapital special articles'),
    'stab_summary': on_manual(28, '0.25% annual appropriation'),
    'stab_text': on_manual(30, 'with an annual appropriation of 0.3 percent of the current year general fund budget'),
    'stab_range': on_manual(30, 'minimum balance of five to eight percent of the current year annual general fund operating budget'),
    'stab_third': on_manual(30, 'the withdrawal should be limited to one-third of the fund’s balance'),
    'stab_refill': on_manual(30, 'replenish the fund to the minimum level within the next two fiscal years'),
    'special': on_manual(30, 'minimum target balance total in the range of three to five percent'),
    'opeb_full': on_manual(47, 'Achieving full funding of the liability requires the Town to commit to funding its actuarially determined contribution (ADC) each year'),
    'opeb_10': on_manual(47, 'Annually appropriate at least 10% of the Town’s certified free cash'),
    'opeb_study': on_manual(46, 'will obtain actuarial analyses of the Town’s OPEB liability every two years'),
    'capital': on_manual(21, 'the Town will strive to appropriate two to three percent of the annual general fund budget, net of debt, to capital investment'),
    'debt_total': on_manual(24, 'Total debt service, including debt exclusions and any self-supporting debt, shall be limited to 11 percent of total operating revenues, with a target balance of five to seven percent'),
    'debt_levy': on_manual(24, 'Debt service within the levy limit (non-excluded) will be between two and four percent of the general fund budget'),
    'debt_roll': on_manual(25, 'the amount of service of the maturing debt should be annually appropriated to special purpose stabilization fund'),
    'receipts': on_manual(34, 'Estimates for local receipts (e.g., motor vehicle excise, inspection fees, etc.) will not exceed 90% of the prior year’s actual collections'),
    'accuracy': on_manual(33, 'review the performance accuracy of prior-year forecasts'),
    'too_low': on_manual(33, 'underestimated projections may result in exce ss revenue that is unavailable to benefit the public'),
    'test_first': on_manual(3, 'The Town should analyze its current financial operations and existing policies to determine the appropriate benchmarks and metrics before adopting these policies'),
}

# The draft's free cash split, in its own order (pdf pages 29-30). Each share is a FLOOR;
# capital is "at least 20 ... no more than 30", other one-time costs "the lesser of 10 percent
# or $250,000". Asserted above, applied in split().
SPLIT = [
    ('keep', 'Kept back for next year', D('0.20')),
    ('general', 'General stabilization', D('0.05')),
    ('special', 'Special purpose funds', D('0.10')),
    ('opeb', 'Retiree health trust', D('0.10')),
    ('capital', 'Cash capital', D('0.20')),
    ('other', 'Other one-time costs', None),       # lesser of 10% or $250,000
]
OTHER_CAP = D('250000')
TREND_FROM = 2017   # the first year the databank's general stabilization equals the annual report's
OTHER_SHARE = D('0.10')


def money(x):
    return D(str(x)).quantize(D('1'))


# ---------------------------------------------------------------- the state's databank exports

def _xlsx(rel):
    import openpyxl
    ws = openpyxl.load_workbook(p(rel), read_only=True, data_only=True).worksheets[0]
    it = ws.iter_rows(values_only=True)
    h = [str(x) for x in next(it)]
    return [dict(zip(h, r)) for r in it]


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def peers():
    import json
    d = json.load(io.open(os.path.join(ROOT, 'fy28', 'public', 'data', 'free-cash.json'), encoding='utf-8'))
    towns = sorted(x['town'] for x in d['peers'])
    if 'Lunenburg' not in towns or len(towns) != 9:
        fail('the free cash peer set changed: %s' % towns)
    return towns


def dls_stabilization():
    """{(town, fy): dict(general, special, total, budget)} for the peer towns, Schedule A year."""
    T = set(peers())
    out = {}
    for r in _xlsx(DLS_STAB):
        if r['Municipality'] in T and _num(r['Stabilization Fund Balance']) is not None:
            out[(r['Municipality'], int(r['Schedule A Fiscal Year']))] = dict(
                general=_num(r['Stabilization Fund Balance']),
                special=_num(r['Special Purpose Stabilization Fund Balance']),
                total=_num(r['Total Stabilization Fund Balance']),
                budget=_num(r['Operating Budget']))
    return out


def dls_free_cash():
    """{(town, fy): dict(amount, budget, certified)}: fy is the year it is available in."""
    T = set(peers())
    out = {}
    for r in _xlsx(DLS_FC):
        if r['Municipality'] in T and _num(r['Certified Free Cash as of 7/1']) is not None:
            out[(r['Municipality'], int(r['Fiscal Year']))] = dict(
                amount=_num(r['Certified Free Cash as of 7/1']), budget=_num(r['Operating Budget Prior Year']),
                certified=r['Date Certified'])
    return out


def dls_debt():
    T = set(peers())
    out = {}
    for r in _xlsx(DLS_DEBT):
        if r['Municipality'] in T and _num(r['GF Debt Service (Schedule A Part 2)']) is not None:
            out[(r['Municipality'], int(r['Fiscal Year']))] = dict(
                service=_num(r['GF Debt Service (Schedule A Part 2)']), budget=_num(r['Total Budget']))
    return out


# ---------------------------------------------------------------- Lunenburg's own records

def fact_sheet():
    """The Town's free cash fact sheet: {fy available: (certified, prior-year budget, date)}."""
    out = {}
    for r in csv.DictReader(io.open(p('data/free-cash-history-fincom.csv'), encoding='utf-8')):
        out[int(r['fiscal_year'])] = (D(r['certified_free_cash']), D(r['prior_year_operating_budget']),
                                      r['date_certified'])
    return out


def annual_report_stabilization():
    """General stabilization year-end ending cash, by fiscal year, from the trust tables."""
    out = {}
    for r in csv.DictReader(io.open(p('data/stabilization-balances.csv'), encoding='utf-8')):
        if r['name'].strip() == 'STABILIZATION' and r['ending_cash']:
            out[int(r['fy'])] = D(r['ending_cash'])
    return out


def fy2025_general_stabilization():
    """Two printed figures for one balance at 30 June 2025. Returned as both; never merged."""
    ar = io.open(p(AR25_TXT), encoding='utf-8').read()
    m = re.search(r'8124 Stabilization Fund\s+([\d,]+\.\d\d)', ar)
    cash = re.search(r'Bartholomew Stabilization Fund ([\d,]+\.\d\d)\$', ar)
    if not (m and cash and m.group(1) == cash.group(1)):
        fail('the FY2025 annual report no longer prints one general stabilization figure twice')
    if 'TRUST FUND BALANCE' not in ar or '(unaudited)' not in ar:
        fail('the FY2025 trust fund table is no longer marked unaudited')
    au = io.open(p(AUDIT_TXT), encoding='utf-8').read()
    a = re.search(r'stabilization funds totaled \$([\d,]+), \$([\d,]+), \$([\d,]+), \$([\d,]+) and \$([\d,]+)', norm(au))
    if not a or 'general, zoning, vehicle and equipment, health insurance, and opiod' not in norm(au):
        fail('the FY2025 audit no longer lists the five stabilization balances in that order')
    return dict(report=D(m.group(1).replace(',', '')), audit=D(a.group(1).replace(',', '')),
                audit_all=[D(x.replace(',', '')) for x in a.groups()])


def audit_fund_balance():
    au = norm(io.open(p(AUDIT_TXT), encoding='utf-8').read())
    m = re.search(r'Unassigned…+ … ([\d,]+)', au)
    t = re.search(r'TOTAL FUND BALANCES…+ … ([\d,]+)', au)
    if not (m and t):
        fail('the audit balance sheet no longer reads')
    if 'total fund balance represents 25% of total general fund expenditures' not in au:
        fail('the audit no longer states total fund balance as 25% of expenditures')
    return dict(unassigned=D(m.group(1).replace(',', '')), total=D(t.group(1).replace(',', '')),
                pct_expenditures=25)


OPEB_ROWS = [
    ('service', 'Service Cost'), ('interest', 'Interest'), ('terms', 'Changes of benefit terms'),
    ('experience', 'Differences between expected and actual experience'),
    ('assumptions', 'Changes of assumptions'), ('benefits_l', 'Benefit payments'),
    ('net_change_l', 'Net change in total OPEB liability'), ('begin_l', 'Total OPEB liability - beginning'),
    ('total', 'Total OPEB liability - ending (a)'),
    ('contrib', 'Employer contributions'), ('contrib_payg', 'Employer contributions for OPEB payments'),
    ('income', 'Net investment income'), ('benefits_p', 'Benefit payments'),
    ('net_change_p', 'Net change in plan fiduciary net position'),
    ('begin_p', 'Plan fiduciary net position - beginning of year'),
    ('trust', 'Plan fiduciary net position - end of year (b)'),
    ('net', 'Net OPEB liability - ending (a)-(b)'),
]


def opeb_schedule():
    """The audit's nine-year schedule (pdf page 78), every identity it prints re-added."""
    txt = io.open(p(AUDIT_TXT), encoding='utf-8').read()
    i = txt.find('Schedule of changes in the Town’s net OPEB liability and related ratios \nJune 30')
    if i < 0:
        fail('the OPEB schedule is not where it was')
    block = txt[i:i + 6000].split('\n')
    years = [int(y) for y in re.findall(r'20\d\d', block[2])]
    if years != list(range(2017, 2026)):
        fail('the OPEB schedule years are %s' % years)

    def nums(line):
        line = line.split('…')[-1] if '…' in line else line
        line = re.sub(r'^[^$\d(\-]*', '', line)
        out = []
        for tok in re.findall(r'\(?-?[\d,]+\)?|(?<![\w])-(?![\w\d])', line.replace('$', ' ')):
            if tok == '-':
                out.append(D(0))
            else:
                neg = tok.startswith('(')
                v = D(tok.strip('()').replace(',', ''))
                out.append(-v if neg else v)
        return out

    rows, used, seen_benefit = {}, set(), 0
    for key, label in OPEB_ROWS:
        for n, line in enumerate(block):
            if n in used or not norm(line).startswith(label):
                continue
            if label == 'Benefit payments':
                pass
            vals = nums(norm(line)[len(label):])
            if len(vals) != 9:
                continue
            rows[key] = dict(zip(years, vals))
            used.add(n)
            break
        else:
            fail('the OPEB schedule has no nine-figure row %r' % label)
    pct = re.findall(r'([\d.]+)%', ' '.join(block[block.index(next(l for l in block if l.startswith('total OPEB liability…'))):][:1]))
    if len(pct) != 9:
        fail('the funded-ratio row did not read nine values')
    for y in years:
        r = {k: v[y] for k, v in rows.items()}
        if r['service'] + r['interest'] + r['terms'] + r['experience'] + r['assumptions'] + r['benefits_l'] != r['net_change_l']:
            fail('FY%d: the liability changes do not add to their printed net change' % y)
        if r['begin_l'] + r['net_change_l'] != r['total']:
            fail('FY%d: beginning plus change is not the ending liability' % y)
        if r['contrib'] + r['contrib_payg'] + r['income'] + r['benefits_p'] != r['net_change_p']:
            fail('FY%d: the trust changes do not add to their printed net change' % y)
        if r['begin_p'] + r['net_change_p'] != r['trust']:
            fail('FY%d: the trust does not roll forward' % y)
        if r['total'] - r['trust'] != r['net']:
            fail('FY%d: total less trust is not the printed net liability' % y)
    funded = dict(zip(years, [D(x) for x in pct]))
    for y in years:
        computed = (rows['trust'][y] / rows['total'][y] * 100).quantize(D('0.01'))
        if abs(computed - funded[y]) > D('0.01'):
            fail('FY%d: the printed funded ratio %s%% is not trust / liability (%s%%)' % (y, funded[y], computed))
    c = re.search(r'June 30, 2025…+ … \$ ([\d,]+) \$ \(([\d,]+)\) \$ ([\d,]+)', norm(txt))
    if not c:
        fail('the FY2025 contribution schedule did not read')
    adc, made, short = (D(x.replace(',', '')) for x in c.groups())
    if adc - made != short:
        fail('the FY2025 contribution deficiency does not foot')
    if made != rows['contrib'][2025] + rows['contrib_payg'][2025]:
        fail('the FY2025 contribution in the two schedules differs')
    return dict(years=years, rows=rows, funded=funded, adc=adc, contributed=made, deficiency=short)


def capital_history():
    out = {}
    for r in csv.DictReader(io.open(p('data/capital-funding-history.csv'), encoding='utf-8')):
        out[int(r['fy'])] = {k: D(v) for k, v in r.items() if k != 'fy'}
    return out


# ---------------------------------------------------------------- the derived figures

def split(free_cash):
    """The draft's minimums applied to one year's free cash. Returns [(key, label, amount)]."""
    out = []
    for key, label, share in SPLIT:
        if share is None:
            amt = min(free_cash * OTHER_SHARE, OTHER_CAP)
        else:
            amt = free_cash * share
        out.append((key, label, amt))
    return out


def build():
    """Everything the pages state, in one dict, after every cross-check."""
    fs = fact_sheet()
    fc_dls = dls_free_cash()
    st = dls_stabilization()
    debt = dls_debt()
    ar = annual_report_stabilization()
    T = peers()

    # FREE CASH: the Town's fact sheet and the state's databank, the same figure every year.
    for fy, (amt, bud, _) in fs.items():
        d = fc_dls.get(('Lunenburg', fy))
        if not d or money(d['amount']) != amt or money(d['budget']) != money(bud):
            fail('FY%d free cash: the fact sheet (%s on %s) and the DLS databank (%s) differ'
                 % (fy, amt, bud, d))
    latest = max(fs)
    if ('Lunenburg', latest + 1) in fc_dls:
        fail('a later free cash certification is now in the databank: rebuild the worked example on it')
    fc, fc_budget, fc_date = fs[latest]

    # STABILIZATION: the databank against the annual reports, to the dollar.
    # Before FY2017 the databank has no special-purpose column, and its "stabilization fund" is
    # larger than the general fund the annual report prints: for FY2014 and FY2015 it equals the
    # general fund PLUS the zoning incentive stabilization fund, to the dollar. So the series is
    # like for like from FY2017 only, and starts there (TREND_FROM).
    matched, earlier = [], []
    zoning = {}
    for r in csv.DictReader(io.open(p('data/stabilization-balances.csv'), encoding='utf-8')):
        if r['code'] == '8129' and r['ending_cash']:
            zoning[int(r['fy'])] = D(r['ending_cash'])
    for fy, v in ar.items():
        d = st.get(('Lunenburg', fy))
        if not d:
            continue
        g = D(str(d['general']))
        if fy >= TREND_FROM:
            if abs(g - v) > 1:
                fail('FY%d general stabilization: annual report %s, databank %s' % (fy, v, g))
            matched.append(fy)
        else:
            earlier.append(fy)
    if not all(money(D(str(st[('Lunenburg', y)]['general']))) == money(ar[y] + zoning[y]) for y in (2014, 2015)):
        fail('the pre-FY2017 databank figure is no longer general plus zoning in FY2014 and FY2015')
    s25 = fy2025_general_stabilization()
    if money(st[('Lunenburg', 2025)]['general']) != money(s25['report']):
        fail('the databank FY2025 general stabilization is not the annual report figure')

    # THE DRAFT'S OWN TABLE (pdf page 31) prints a general stabilization balance per year; each
    # equals the annual report's ending balance of the year BEFORE, to the dollar.
    pg = manual_page(31)
    m = re.search(r'General Stabilization Fund Balance ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+)', pg)
    if not m:
        fail('the draft no longer prints its stabilization balance row')
    draft_bal = dict(zip([2021, 2022, 2023, 2024], [D(x.replace(',', '')) for x in m.groups()]))
    prior = {fy: v for fy, v in draft_bal.items() if abs(ar.get(fy - 1, D(-9)) - v) < 1}
    if len(prior) != 4:
        fail('the draft\'s stabilization balances no longer equal the prior year-end: %s' % draft_bal)

    budget25 = D(str(st[('Lunenburg', 2025)]['budget']))
    if money(budget25) != money(fc_budget):
        fail('the FY2025 operating budget differs between the two databank reports')

    stab_pct = {fy: D(str(v['general'])) / D(str(v['budget'])) * 100
                for (t, fy), v in st.items() if t == 'Lunenburg' and fy >= TREND_FROM}
    fc_pct = {fy: amt / bud * 100 for fy, (amt, bud, _) in fs.items()}

    peer_stab = {t: D(str(st[(t, 2025)]['general'])) / D(str(st[(t, 2025)]['budget'])) * 100
                 for t in T if (t, 2025) in st}
    peer_fc = {t: D(str(fc_dls[(t, latest)]['amount'])) / D(str(fc_dls[(t, latest)]['budget'])) * 100
               for t in T if (t, latest) in fc_dls}
    peer_debt = {t: D(str(debt[(t, 2025)]['service'])) / D(str(debt[(t, 2025)]['budget'])) * 100
                 for t in T if (t, 2025) in debt}
    for name, x in (('stabilization', peer_stab), ('free cash', peer_fc), ('debt', peer_debt)):
        if len(x) != len(T):
            fail('%s: %d of %d peer towns hold a figure' % (name, len(x), len(T)))

    sp = split(fc)
    claimed = sum(a for _, _, a in sp)
    debt25 = D(str(debt[('Lunenburg', 2025)]['service']))
    cap = capital_history()
    return dict(
        fact_sheet=fs, latest=latest, fc=fc, fc_budget=fc_budget, fc_date=fc_date,
        split=sp, claimed=claimed, unclaimed=fc - claimed, today_fixed=fc * D('0.10'),
        point=fc / 100,
        stab_matched=sorted(matched), stab_earlier=sorted(earlier), stab25=s25, draft_bal=draft_bal, budget25=budget25,
        stab_pct=stab_pct, fc_pct=fc_pct, peer_stab=peer_stab, peer_fc=peer_fc, peer_debt=peer_debt,
        stab_deposit=(budget25 * D('0.0025'), budget25 * D('0.003')),
        reserves_band=(fc_budget * D('0.13'), fc_budget * D('0.20')),
        fund_balance=audit_fund_balance(), opeb=opeb_schedule(),
        debt25=debt25, capital_band=((budget25 - debt25) * D('0.02'), (budget25 - debt25) * D('0.03')),
        capital=cap, peers=T)
