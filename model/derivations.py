"""Line-item derivation of every rolled-up number this app quotes.

The app repeatedly states figures like "athletics costs $451,830" or "all administration
is $2,633,246". Each of those is a roll-up of many budget lines, and until now the
roll-up existed only as a constant. This module rebuilds every one of them from the
district's own line-item budget -- `sources/data/lps-budget-lines.csv`, extracted from
the FY27 budget document -- and checks the rebuilt total against the constant the rest
of the model uses.

Three kinds of derivation:

  lines      a set of budget lines summed in one scenario column. Fully checkable.
  arithmetic one figure computed from other derived figures (a difference, a share).
  catalog    a roll-up of entries in `catalog.py` rather than of raw budget lines. These
             are how the app groups spending into things a voter can name, and some
             entries are OUR estimate rather than a published line. Flagged as such.

`reconciled` is False wherever the rebuilt total does not match the constant. Nothing is
hidden: an unreconciled derivation still ships, with the gap shown.
"""
import csv
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), '..',
                        'sources', 'data', 'lps-budget-lines.csv')

SCENARIOS = {
    'fy26_final':         'FY26 final',
    'fy27_restoration':   'FY27 Restoration',
    'fy27_core':          'FY27 Core',
    'fy27_level_service': 'FY27 Level Service',
    'fy27_balanced':      'FY27 Balanced (adopted)',
}

SOURCE_DOC = ('FY27 line-item budget, Lunenburg Public Schools, 23 March 2026 '
              '(sources/data/lps-budget-lines.csv)')

# Rows that are subtotals in the source spreadsheet, never summed as detail.
_TOTAL_GROUPS = ('TOTAL EXPENSES', 'TOTAL SALARIES')


def _rows():
    with open(CSV_PATH, newline='') as fh:
        return list(csv.DictReader(fh))


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


ROWS = _rows()
DETAIL = [r for r in ROWS if r['function_group'] not in _TOTAL_GROUPS
          and r['function_group']]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

def by_groups(*groups):
    """Every line inside one or more DESE function groups."""
    want = set(groups)
    return lambda r: r['function_group'] in want


def by_lines(*pairs):
    """Named (function group, line item) pairs -- for roll-ups that cut across groups."""
    want = set(pairs)
    return lambda r: (r['function_group'], r['line_item']) in want


def _collect(pred, column, line_notes=None):
    """Sum the selected lines. `line_notes` attaches a caution to named line items --
    used where the budgeted figure is sound as a transcription but soft as a fact."""
    line_notes = line_notes or {}
    lines, total = [], 0.0
    for r in DETAIL:
        if not pred(r):
            continue
        amount = _num(r[column])
        if amount == 0:
            continue          # a $0 placeholder row adds nothing and only adds noise
        entry = dict(group=r['function_group'], item=r['line_item'], amount=amount)
        note = line_notes.get(r['line_item'])
        if note:
            entry['note'] = note
        history = {c: _num(r[c]) for c in
                   ('fy23_actual', 'fy24_actual', 'fy25_actual', 'fy26_final',
                    'fy26_actual_td', 'fy26_encumb_td')}
        if note and any(history.values()):
            entry['history'] = {k: v for k, v in history.items() if v}
        lines.append(entry)
        total += amount
    return lines, total


# ---------------------------------------------------------------------------
# The roll-ups, each with the constant it must reproduce
# ---------------------------------------------------------------------------

_ADMIN_CENTRAL_GROUPS = (
    '1110 - School Committee',
    '1210 - Superintendent Office',
    '1210 - Superintendent Office Salaries',
    '1230-District Wide Administration',
    '1410 - Business Office',
    '1410 - Business Office Salaries',
    '1420 - Human Resources Salaries',
    '1430 - Legal',
    '1450 - Info Management & Tech Expense',
    '1450 - Administrative Technology',
)

_ADMIN_BUILDING_GROUPS = (
    '2210 - P.S. Principals Office', '2210 - P.S. Principal Office Salaries',
    '2210 - E.S. Principals Office', '2210 - E.S. Principal Office Salaries',
    '2210 - M.S. Principals Office', '2210 - Middle School Principal Office Salaries',
    '2210 - H.S. Principals Office', '2210 - H.S. Principal Office Salaries',
)

_ADMIN_CURRICULUM_GROUPS = (
    '2110 - Special Education',
    '2110 - System Curriculum Adop',
    '2110 - Curriculum/Spec Ed Directors',
    '2110 - Special Education Clerical',
)

_TECH_LINES = (
    ('1410 - Business Office', "Admin Contr'd Technology Support (TSA)"),
    ('1450 - Info Management & Tech Expense', 'Admin Tech Contracted Services'),
    ('1450 - Administrative Technology', 'Technology Personnel'),
    ('2110 - Special Education', 'Specl Ed Computer Contracted Services'),
    ('2415 - E.S. Other Instr. Materials', 'E.S. Audio Visual/ Technology Supplies'),
    ('2451 - Instructional Tech.', 'P.S. Computer Contractual Services'),
    ('2451 - Instructional Tech.', 'E.S. Computer Contractual Services'),
    ('2451 - Instructional Tech.', 'M.S. Computer Contractual Services'),
    ('2451 - Instructional Tech.', 'H.S. Computer Contractual Services'),
    ('2451 - Instructional Tech.', 'Computer Supplies/District Wide'),
    ('2710 - Guidance Exp.', 'H.S. Lease of Guidance Software'),
    ('4400 - Networking / Telecommunications', 'Networking Contracted Service'),
    ('7400 - Replace Equipment', 'COMPUTERS - Purchase & Lease'),
)

_ART_SUPPLY_LINES = (
    ('2415 - P.S. Other Instr. Materials', 'P.S. Art Supplies'),
    ('2415 - E.S. Other Instr. Materials', 'E.S. Art Supplies'),
    ('2415 - M.S. Other Instr. Materials', 'M.S. Art Supplies'),
    ('2415 - H.S. Other Instr. Materials', 'H.S. Art Supplies'),
)

_MUSIC_SUPPLY_LINES = (
    ('2415 - E.S. Other Instr. Materials', 'E.S. Music'),
    ('2420 - M.S. Instr.Equipment', 'M.S. Band/Music Supplies'),
    ('2420 - H.S. Instr. Equipment', 'H.S. Band/Music Dues and Fees'),
    ('2420 - H.S. Instr. Equipment', 'BAND/MUSIC SUPPLIES'),
    ('2420 - H.S. Instr. Equipment', 'MUSIC MARCHING BAND'),
    ('2420 - H.S. Instr. Equipment', 'MUSIC EQUIPMENT'),
    ('4230 - M.S. Repairs', 'M.S. Repair Music Equipment'),
    ('4230 - H.S. Repairs', 'H.S. Repair Music Equipment'),
)

_BAND_TRANSPORT_LINES = (
    ('2440 - Other Instr.Services', 'M.S. Band/Music Transportation'),
    ('2440 - Other Instr.Services', 'H.S. Band/Music Transportation'),
)

_ATHLETICS_GROUPS = ('3510 - Athletic Expenses', '3510 - Athletics Salaries')


# Cautions attached to individual lines: correctly transcribed, but soft as facts.

AD_NOTE = (
    'Not the cost of an athletic director, and probably out of date. As budgeted this is a '
    'STIPEND: the salaried position ran $85,977 / $90,200 / $96,044 in FY23-FY25 actuals '
    'and $74,406 in FY26, then drops to $20,000 in ALL FOUR FY27 scenarios — including '
    'Restoration, the district\'s own ideal budget. The Multi-Scenario Addendum books a '
    '$10,000 Athletic Director Stipend under "Changes since 2/24/26", alongside a $110,195 '
    'reduction from High School Principal / Assistant Principal. '
    'SINCE THEN, and not reflected in any published budget: the athletic director who held '
    'the role left, and the position was returned to full time. The School Committee had '
    'debated exactly this, with the shared teaching-and-athletics arrangement described as '
    'unsustainable. The budget still says $20,000. On the FY23-FY25 actuals a full-time '
    'director runs '
    '$86,000-$96,000, so athletics plausibly costs $65,000-$75,000 more than the adopted '
    'line shows. That range is OUR estimate — no published document records the change or '
    'its cost, and it is the first thing to ask the Business Manager about.')

TRANSPORT_NOTE = 'Budgeted well above what athletics has ever actually spent. Actuals were $39,880 (FY23), $40,000 (FY24) and $87,822 (FY25); the line was then rebased to $127,550 for FY26 and level-funded into FY27. As of the 23 March 2026 budget, FY26 had spent $47,847 with $13,169 encumbered — $61,016 committed against $127,550, with only the spring season left to run. The district asked itself this exact question in the spreadsheet margin ("Actuals in munis are tracking well below FY26 budget, can FY27 be reduced?") and answered "Yes, level funded". Treat it as a budget figure, not a spending figure.'

LINE_RULES = [
 dict(id='athletics_total',
      question='How did you calculate total athletics cost?',
      label='Athletics — the full program',
      column='fy27_level_service', expected=451_830,
      selector=by_groups(*_ATHLETICS_GROUPS),
      lineNotes={'Athletic Transportation': TRANSPORT_NOTE,
                 'Athletic Director': AD_NOTE},
      answer='Two DESE function groups, added up: 3510 Athletic Expenses (transport, '
             'insurance, dues, equipment) and 3510 Athletics Salaries (director, trainer, '
             'secretary, all coaching stipends). Nothing else is counted.',
      notes=['We use the Level Service column — what it costs to run athletics as it '
             'was, before the FY27 cuts. That is the honest denominator for "can fees '
             'pay for athletics", because a fee has to fund the programme you want, not '
             'the one that survived.',
             'Club and after-school advisor stipends (3520, $11,731) are NOT in this '
             'figure. They are activities, not athletics, and are counted separately.',
             'This is gross cost. Fee income is invisible in the budget document, which '
             'is expenditures only — so we cannot tell you whether $451,830 is before or '
             'after the fees families already pay.',
             'Two lines in this total do not mean what their labels suggest, and they '
             'pull in opposite directions: athletic transportation is budgeted far above '
             'what athletics has ever spent, and the athletic director line is a $20,000 '
             'stipend where a ~$90,000 salaried position used to be. Both are flagged in '
             'the table. $451,830 is what the district budgeted, which is the right basis '
             'for a budget argument — but it is not a measurement of what athletics '
             'costs to run.']),

 dict(id='athletics_remaining',
      question='What survives of athletics in the adopted budget?',
      label='Athletics — what the adopted FY27 budget funds',
      column='fy27_balanced', expected=217_908,
      selector=by_groups(*_ATHLETICS_GROUPS),
      lineNotes={'Athletic Director': AD_NOTE},
      answer='The same two function groups, read in the Balanced column — the budget '
             'Town Meeting actually adopted after both overrides failed.',
      notes=['The exact sum is $217,908.50. The app rounds to $217,908.',
             'All athletic transportation ($127,550) and the middle school / freshman '
             'coaching stipends ($14,415) fall to zero here. Coaching stipends drop from '
             '$159,444 to $87,331 and the trainer is halved.']),

 dict(id='tech_total',
      question='How did you calculate total technology spend?',
      label='Technology — contracts, licences, devices and staff',
      column='fy27_balanced', expected=638_675,
      selector=by_lines(*_TECH_LINES),
      answer='Technology is not one function group — it is scattered across eight of '
             'them. These are the individual lines that are technology spending, named '
             'one by one.',
      notes=['Device leases ($185,065) sit under 7400 Replace Equipment; the guidance '
             'software lease ($13,800) sits under Guidance. Neither would be found by '
             'looking at a "technology" heading.',
             'Webmaster and tech-support stipends ($11,670) are excluded — they are '
             'stipends paid to staff, not technology purchasing. Including them would '
             'make the figure $650,345.']),

 dict(id='admin_central',
      question='What counts as central office administration?',
      label='Administration — central office',
      column='fy27_balanced', expected=1_040_389,
      selector=by_groups(*_ADMIN_CENTRAL_GROUPS),
      answer='Every 1000-series function group: School Committee, Superintendent, '
             'District-Wide Administration, Business Office, Human Resources, Legal, and '
             'Information Management / Administrative Technology — salaries and expenses '
             'both.',
      notes=['This is one superintendent, one business manager and one HR specialist for '
             'four schools.']),

 dict(id='admin_building',
      question='What counts as building administration?',
      label='Administration — the four principals’ offices',
      column='fy27_balanced', expected=1_183_773,
      selector=by_groups(*_ADMIN_BUILDING_GROUPS),
      answer='All eight 2210 Principals’ Office groups — the four schools’ principals, '
             'assistant principals and office secretaries, salaries and expenses.',
      notes=['Unchanged across all four FY27 scenarios: no principal’s office was cut or '
             'restored in any version of the budget.',
             'The FY27 budget did cut an Assistant Principal through attrition, so the '
             'Primary School and Turkey Hill now share one.']),

 dict(id='admin_curriculum',
      question='What else is in the administration total?',
      label='Administration — curriculum & special education administration',
      column='fy27_balanced', expected=409_084,
      selector=by_groups(*_ADMIN_CURRICULUM_GROUPS),
      answer='The 2110 groups: the Curriculum and Special Education Directors, special '
             'education clerical staff, and the district curriculum adoption line.',
      notes=['Reasonable people put these on either side of the line. They are '
             'administrators, not teachers — but special education administration is '
             'largely a legal compliance function, not a discretionary one.']),

 dict(id='health_total',
      question='How did you calculate the health insurance figure?',
      label='Health insurance',
      column='fy27_balanced', expected=3_994_071,
      selector=by_lines(('5200 - Insurance Programs', 'Health Insurance')),
      answer='A single budget line. No roll-up involved.',
      notes=['This is the school department’s share only. The Town, not the district, '
             'controls the insurance group and negotiates plan design.',
             'It fell from $4,389,135 in the Restoration scenario to $3,994,071 in the '
             'adopted budget — because fewer positions means fewer people to insure.']),

 dict(id='transport_gened',
      question='How much is general education transportation?',
      label='Transportation — general education',
      column='fy27_balanced', expected=1_053_360,
      selector=by_lines(('3300 - Student Transportation',
                         'General Education Transportation')),
      answer='A single budget line.',
      notes=['Unchanged across all four scenarios.']),

 dict(id='transport_sped',
      question='How much is special education transportation?',
      label='Transportation — special education',
      column='fy27_balanced', expected=649_953,
      selector=by_lines(('3300 - Student Transportation',
                         'Special Education Transportation - System')),
      answer='A single budget line.',
      notes=['Cannot be charged for. Special education transport is an IEP entitlement '
             'under federal law, so no fee can be applied to it.']),

 dict(id='art_supplies',
      question='How did you calculate art supplies across all four schools?',
      label='Art supplies — all four schools',
      column='fy27_balanced', expected=30_685,
      selector=by_lines(*_ART_SUPPLY_LINES),
      answer='One art supply line per school, added together.',
      notes=[]),

 dict(id='music_supplies',
      question='How did you calculate band and music supplies?',
      label='Band & music supplies, equipment and repair',
      column='fy27_balanced', expected=17_073,
      selector=by_lines(*_MUSIC_SUPPLY_LINES),
      answer='Every music line that is supplies, equipment, dues or instrument repair, '
             'across all four schools. Instrument repair sits under building Repairs, not '
             'under Instructional Equipment, so it is easy to miss.',
      notes=['Band and music transportation is NOT in this figure — it is counted '
             'separately, because the adopted budget cut it to zero.']),

 dict(id='band_transport',
      question='How much was band and music transportation?',
      label='Band & music transportation',
      column='fy27_level_service', expected=5_000,
      selector=by_lines(*_BAND_TRANSPORT_LINES),
      answer='Two lines — middle school and high school. Shown at Level Service because '
             'the adopted budget cut both to zero.',
      notes=['$5,000 buys every band and chorus trip in the district. It was cut.']),

 dict(id='clubs',
      question='How did you calculate the cost of all clubs?',
      label='Clubs & after-school advisors',
      column='fy27_balanced', expected=11_731,
      selector=by_lines(('3520 - After School Advisor Salaries',
                         'H.S. After School Advisors')),
      answer='A single line: 3520 After School Advisor Salaries. It covers every advised '
             'club at the high school.',
      notes=['There is no equivalent line for the other three schools.']),
]


ARITHMETIC_RULES = [
 dict(id='athletics_cut',
      question='How much athletics has already been cut?',
      label='Athletics — already cut to reach the adopted budget',
      expected=233_922,
      terms=[('athletics_total', 1, 'Athletics at level service'),
             ('athletics_remaining', -1, 'Athletics in the adopted budget')],
      answer='The difference between the two athletics figures above.',
      notes=['More than half the athletics programme, by dollars, is already gone.']),

 dict(id='admin_total',
      question='How did you calculate total administration?',
      label='Administration — everything',
      expected=2_633_246,
      terms=[('admin_central', 1, 'Central office'),
             ('admin_building', 1, 'The four principals’ offices'),
             ('admin_curriculum', 1, 'Curriculum & special education administration')],
      answer='The three administration roll-ups above, added together.',
      notes=['9.9% of the school budget — smaller than most people guess when they '
             'propose "cut administration" as the answer.',
             'DESE independently puts Lunenburg administration at $1,158,507 in FY24, '
             'below every peer district except Ashburnham-Westminster. DESE counts a '
             'narrower set of functions than this total does.']),
]


# Roll-ups that come from the program catalog rather than from raw budget lines.
CATALOG_RULES = [
 dict(id='extras_athletics', cat='athletics', expected=466_244,
      question='What does "cutting every sport" actually mean?',
      label='Every sport, coach, trainer and athletic bus',
      answer='The athletics entries in the program catalog — the same money as the '
             'athletics roll-up above, but broken into the things a voter can name.',
      notes=['This totals $466,244 against the FY27 Restoration column’s $466,245. The '
             '$1 is rounding: the surviving athletics figure is $217,908.50 and the '
             'catalog carries it as $217,908.']),
 dict(id='extras_arts', cat='arts', expected=166_056,
      question='How did you calculate the cost of all arts and music?',
      label='Every band, chorus, art supply and music program',
      answer='The arts entries in the program catalog. Unlike athletics, this one is '
             'NOT purely published: teaching positions are not itemised by subject in '
             'the budget, so the high school music position is our estimate.',
      notes=['The $72,440 high school band and chorus position is our estimate of a 1.0 '
             'FTE music salary. The district has never published a price for cutting it. '
             'Everything else in this list is a published line.']),
 dict(id='extras_activities', cat='activities', expected=11_731,
      question='How did you calculate the cost of all clubs?',
      label='Every club and after-school advisor',
      answer='One catalog entry, backed by one budget line.',
      notes=[]),
]


def _scenario_totals():
    """The four FY27 scenario totals, straight off the spreadsheet's own total row."""
    row = next(r for r in ROWS if r['line_item'] == 'TOTAL ACTUALS & BUDGET:')
    detail = {c: 0.0 for c in SCENARIOS}
    for r in DETAIL:
        for c in SCENARIOS:
            detail[c] += _num(r[c])
    reserve = next((r for r in ROWS if r['line_item'] == 'Salary Reserve'), None)
    out = []
    for col, label in SCENARIOS.items():
        stated = _num(row[col])
        res = _num(reserve[col]) if reserve else 0.0
        rebuilt = detail[col] + res
        out.append(dict(
            column=col, label=label, stated=round(stated, 2),
            detailLines=round(detail[col], 2), salaryReserve=round(res, 2),
            rebuilt=round(rebuilt, 2), delta=round(rebuilt - stated, 2),
            reconciled=abs(rebuilt - stated) < 5.0))
    return out


def build(catalog_programs=None, ladder=None):
    """Return every derivation, with its lines and its reconciliation status."""
    out = []

    for rule in LINE_RULES:
        lines, total = _collect(rule['selector'], rule['column'],
                                rule.get('lineNotes'))
        expected = rule['expected']
        out.append(dict(
            id=rule['id'], kind='lines', question=rule['question'],
            label=rule['label'], answer=rule['answer'], notes=rule['notes'],
            scenario=SCENARIOS[rule['column']], source=SOURCE_DOC,
            lines=[dict(l, amount=round(l['amount'], 2)) for l in lines],
            lineCount=len(lines), total=round(total, 2), expected=expected,
            delta=round(total - expected, 2),
            reconciled=abs(total - expected) < 1.0))

    index = {d['id']: d for d in out}

    for rule in ARITHMETIC_RULES:
        terms, total = [], 0.0
        for ref, sign, label in rule['terms']:
            amount = index[ref]['total'] if ref in index else 0.0
            terms.append(dict(ref=ref, label=label, sign=sign,
                              amount=round(amount, 2)))
            total += sign * amount
        expected = rule['expected']
        out.append(dict(
            id=rule['id'], kind='arithmetic', question=rule['question'],
            label=rule['label'], answer=rule['answer'], notes=rule['notes'],
            scenario='Derived', source='Computed from the roll-ups above',
            terms=terms, total=round(total, 2), expected=expected,
            delta=round(total - expected, 2),
            reconciled=abs(total - expected) < 1.0))
        index[rule['id']] = out[-1]

    if ladder:
        rungs = []
        for r in ladder:
            rungs.append(dict(
                id=r['id'], label=r['label'], addLabel=r.get('addLabel'),
                add=r['add'], running=round(r['total'], 2), scenario=r['scenario'],
                published=r['published'], selfFundFee=r.get('selfFundFee'),
                coverageNow=r.get('coverageNow'), sub=r['sub']))
        out.append(dict(
            id='athletics_ladder', kind='ladder',
            question='What does athletics actually cost — and which number should a fee '
                     'be measured against?',
            label='Athletics, from what was funded to the whole programme',
            answer='Town Meeting passed only the Balanced budget, which funds $217,908 of '
                   'athletics — and zero athletic transportation. A team that cannot get '
                   'to an away game is not a team, so that figure cannot be the test of '
                   'whether athletics pays for itself. Each rung below adds one real '
                   'budget line or scenario delta on top of the one before it, so you can '
                   'pick the basis you think is honest and see what it costs.',
            notes=[
                'The rungs are exact. $217,908.50 + $127,550 + $34,258.50 + $72,113 + '
                '$14,415 = $466,245, which is the district\'s own Restoration and Core '
                'column to the dollar.',
                'Two rungs are OUR construction, not budgets the district published: '
                '"able to travel" and "plus a full-time trainer". Both are built from '
                'published line items, but no scenario in the budget document looks like '
                'them.',
                'Level Service is not the top rung. Level Service cut freshman and middle '
                'school coaching too — only Restoration and Core fund those teams.',
                'The self-funding fee for each rung assumes 5% of participation lost per '
                '$100 above today\'s fee and a 12% waiver rate. Both are our assumptions, '
                'adjustable on the Fees tab. "Out of reach" means revenue peaks below '
                'that rung at any fee.'],
            scenario='Multiple', source='FY27 line-item budget, rung by rung',
            rungs=rungs, total=rungs[-1]['running'], expected=466_245,
            delta=round(rungs[-1]['running'] - 466_245, 2),
            reconciled=abs(rungs[-1]['running'] - 466_245) < 1.0))

    if catalog_programs is not None:
        for rule in CATALOG_RULES:
            entries = [p for p in catalog_programs if p['cat'] == rule['cat']]
            total = sum(p['cost'] for p in entries)
            expected = rule['expected']
            out.append(dict(
                id=rule['id'], kind='catalog', question=rule['question'],
                label=rule['label'], answer=rule['answer'], notes=rule['notes'],
                scenario='Program catalog', source='catalog.py, sourced entry by entry',
                entries=[dict(name=p['name'], amount=p['cost'], status=p['status'],
                              source=p['source'],
                              estimated=p['source'] == 'EST') for p in entries],
                estimatedAmount=sum(p['cost'] for p in entries if p['source'] == 'EST'),
                total=round(total, 2), expected=expected,
                delta=round(total - expected, 2),
                reconciled=abs(total - expected) < 1.0))

    return out


SCENARIO_NOTE = (
    'Rebuilt = every detail line in that column, plus the salary reserve. Stated = the '
    'spreadsheet\'s own "TOTAL ACTUALS & BUDGET" row. The two differ by up to $2 in a '
    '$28 million budget, which is rounding inside the district\'s own file, not a '
    'missing line.')


SOURCE_CODES = {
    'ADD':  'Budget Addendum: Multi-Scenario Financial Analysis, 13 March 2026',
    'LINE': 'FY27 line-item budget',
    'ATRP': 'Additional Town Revenue Spending Plan (September 2026 Special Town Meeting)',
    'PR':   'Town Manager press release, 17 April 2026',
    'EST':  'Our estimate — NOT published by the district',
}


def export(catalog_programs=None, ladder=None):
    return dict(
        derivations=build(catalog_programs, ladder),
        scenarioTotals=_scenario_totals(),
        scenarioNote=SCENARIO_NOTE,
        sourceDoc=SOURCE_DOC,
        sourceCodes=SOURCE_CODES,
        scenarios=SCENARIOS,
    )


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from catalog import PROGRAMS
    from athletics import (PROGRAM_LADDER, self_funding_fee, fee_revenue,
                           EFFECTIVE_ATHLETIC_FEE)
    ladder = [dict(r, selfFundFee=self_funding_fee(r['total']),
                   coverageNow=round(fee_revenue(EFFECTIVE_ATHLETIC_FEE) / r['total'], 4))
              for r in PROGRAM_LADDER]
    data = export(PROGRAMS, ladder)
    bad = 0
    for d in data['derivations']:
        mark = 'ok ' if d['reconciled'] else 'OFF'
        if not d['reconciled']:
            bad += 1
        n = d.get('lineCount') or len(
            d.get('terms') or d.get('entries') or d.get('rungs') or [])
        print(f"  {mark} {d['id']:<22} {d['total']:>14,.2f}  "
              f"expected {d['expected']:>12,}  delta {d['delta']:>9,.2f}  ({n} parts)")
    print()
    for s in data['scenarioTotals']:
        mark = 'ok ' if s['reconciled'] else 'OFF'
        print(f"  {mark} {s['label']:<26} stated {s['stated']:>14,.2f}  "
              f"rebuilt {s['rebuilt']:>14,.2f}  delta {s['delta']:>8,.2f}")
    print(f"\n{bad} unreconciled derivation(s)")
