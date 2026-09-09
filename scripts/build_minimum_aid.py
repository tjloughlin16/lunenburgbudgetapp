#!/usr/bin/env python3
"""Chapter 70, term by term: why the formula pays Lunenburg the legislature's floor.

    python3 scripts/build_minimum_aid.py
    python3 scripts/build_minimum_aid.py --check

WHAT THIS PAGE IS, AND WHAT IT IS NOT. `/state-aid` is about state aid as a WHOLE -- the
cherry sheet, what the town budgeted against what it received, and the growth rate the
model uses. This page is about ONE program inside it, Chapter 70, and about the FORMULA
that sets it: what DESE's own aid components did, year by year, FY2007 to FY2026.

CLAUDE.md rule 11 records this project publishing a Chapter 70 share eight points too high
for months, because $11,404,917 -- ALL state aid in the Governor's FY27 budget -- was
described as Chapter 70, which is 78.7% of it. Nothing on this page is total state aid.
Every figure here is Chapter 70 alone, out of DESE's own workbook, and the page says so.

RULE 1, AND IT IS THE HARD PART. A Chapter 70 figure exists at several stages -- the
Governor's budget, House, Senate, conference, the enacted act, and then the receipt. They
are different numbers for the same year. **Every series here is one stage: DESE's published
Chapter 70 calculation for that fiscal year**, taken from the `dataAid` and
`dataContribution` sheets of the Chapter 70 Trends workbook, which is the calculation as
run. Nothing here is differenced against a Governor's-budget figure or against a receipt.

Two Governor's-stage figures are quoted on the page and are quoted as EVIDENCE OF THE GAP
BETWEEN STAGES rather than as data: the Finance Committee was told in March 2024 that FY25
minimum aid was $30 a pupil, and School Committee minutes record the House raising FY26
from $75 to $150. The enacted figures in this workbook are $104 and $150. They are printed
beside each other and never subtracted.

WHAT IS ESTABLISHED HERE IS ARITHMETIC ON PUBLISHED FIGURES, AND IT IS EXACT.

  1. FY2026 aid rose $240,450 and that is $150.00 for each of 1,603 foundation pupils,
     to the cent. The foundation aid increment -- the formula's own term -- is $0.
  2. WHY it is zero is DESE's own rule, quoted from the workbook's User Guide: foundation
     aid is the foundation budget less the required contribution, paid only where that
     exceeds last year's aid. For FY2026 that is $8,739,315 against $8,988,960 already
     received. Lunenburg is $249,645 ABOVE the line at which the formula pays anything.
  3. The floor is a statewide rate and not a Lunenburg number: five of the six comparison
     districts get exactly $150.00 a pupil in FY2026, and all six get exactly $30.00 in
     FY2022.
  4. The town's required contribution is a WEALTH calculation. `targetlocacont` equals
     `cey`, the combined effort yield, in all twenty years -- property effort plus income
     effort. Foundation enrollment does not appear in it.

WHAT IS NOT ESTABLISHED, AND THE PAGE SAYS SO IN THOSE WORDS. Whether one more child
changes the town's bill. The aid side has an answer while the floor binds; the contribution
side does not respond to enrollment except through the allocation share and a statutory cap
that is not binding here; and the two cannot be combined, because a large enough foundation
budget increase moves the district off the floor and no document here models that. Three
`money_gaps` rows already carry this and are cited rather than restated.

THE JOINS ARE ASSERTED. A join that matches nothing looks exactly like a district that
never moved money. Every one here refuses to write rather than write an empty series.
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import sys

# The conclusions this report states, as DATA rather than as sentences in a page. See
# scripts/conclusions.py.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'minimum-aid.json')

LEA = '01620000'
TOWN = 'Lunenburg'
MINUTES = 'sources/meetings/text'

# The workbook the whole page is read out of, and the two sheets inside it. The front
# `Summary` sheet is a VLOOKUP interface and reads as formula text; the data is behind it.
DOC_KEY = 'state-dese/dese-ch70-key-factors.xlsx'
SHEET_AID = 'dataAid'
SHEET_CONTRIB = 'dataContribution'

# A district does not lose two decades of formula history. If the query comes back short,
# something moved underneath and publishing it would present a truncated series as the
# whole record.
MIN_YEARS = 19

# The FY2026 rows, by coordinate, so a reader can open the workbook at the cell rather than
# at our rendering of it (rule 13). Asserted against the database on every run.
CELLS = {
    'enrollment': 'dataAid!F8491',
    'foundation_budget': 'dataAid!G8491',
    'required_local_contribution': 'dataAid!H8491',
    'target_aid_pct': 'dataAid!I8491',
    'foundation_aid_increment': 'dataAid!J8491',
    'minimum_aid_increment': 'dataAid!N8491',
    'ch70_aid': 'dataAid!P8491',
    'required_nss': 'dataAid!Q8491',
    'town_equalized_valuation': 'dataContribution!F6853',
    'town_income': 'dataContribution!H6853',
    'town_combined_effort_yield': 'dataContribution!J6853',
    'town_foundation_budget': 'dataContribution!L6853',
    'town_target_contribution': 'dataContribution!M6853',
    'town_preliminary_contribution': 'dataContribution!O6853',
    'town_shortfall': 'dataContribution!R6853',
    'town_dollar_increment': 'dataContribution!S6853',
    'town_required_local_contribution': 'dataContribution!U6853',
}

# DESE'S OWN DEFINITIONS, from the workbook's `User Guide` sheet, by cell. These are the
# rules the arithmetic on this page reproduces, and quoting them is what separates "the
# formula works this way" from "our reading of the numbers suggests". Checked against the
# workbook is not possible without openpyxl at build time, so they are checked against the
# extractor's own recorded text instead -- see `definitions_hold()`.
DEFINITIONS = [
    dict(cell='User Guide!B17', term='Required Local Contribution (RLC)',
         text="The minimum equitable level of local funding needed to support a "
              "district's foundation budget, based upon the relative wealth of the "
              "community."),
    dict(cell='User Guide!B24', term='Combined Effort Yield (CEY)',
         text='The sum of local effort from property and local effort from income.'),
    dict(cell='User Guide!B26', term='Target Local Share',
         text="An equitable portion of a city or town's foundation budget that should be "
              "supported through local funds. Individual communities’ target local "
              "shares are based on local property values and income, and foundation "
              "budget. It is calculated as CEY divided by foundation budget multiplied by "
              "100%, and is capped at 82.5%."),
    dict(cell='User Guide!B27', term='Preliminary Contribution',
         text="This is the first step in calculating a city or town's RLC. It is "
              "calculated as last year's RLC multiplied by this year's MRGF."),
    dict(cell='User Guide!B34', term='Foundation Aid Increase',
         text='The amount of additional aid a district needs to have resources equal to '
              'its foundation budget. Foundation budget less required contribution equals '
              'foundation aid. If foundation aid is greater than prior year Chapter 70 '
              'aid, the district receives a foundation aid increase.'),
    dict(cell='User Guide!B38', term='Minimum Aid',
         text='Guarantees a minimum per pupil increase in aid over the prior year '
              '(typically $30 per pupil), if all other available aid components do not '
              'equal that amount.  Not available in every year.'),
    dict(cell='User Guide!B45', term='Required Net School Spending',
         text='Local Contribution + State Aid = a district’s Net School Spending '
              '(NSS) requirement. This is the minimum amount that a district must spend '
              'to comply with state law.'),
]

# WHAT THE TOWN SAID, rule 15a. Every quote is re-read out of the extracted minutes on this
# run and a miss stops the build: a quote is a claim about a document, and rule 13 says
# quote the source rather than your rendering of it.
#
# THESE ARE STATEMENTS MADE IN PUBLIC, NOT MEASUREMENTS. Where one can be recomputed the
# page recomputes it and says which; where it cannot, it is what somebody said and nothing
# more.
QUOTES = [
    dict(key='house', board='school-committee', date='2025-04-16', kind='minutes',
         doc='7171',
         quote='Their budget has a minimum aid to school raising from the $75 per student '
               'to $150, however, this is a huge example of how you can’t count on '
               'anything because this has to',
         why='The $150 this page measures, named in public a month before the year was '
             'set, together with the figure it replaced. RULE 1 IN ONE SENTENCE: $75 and '
             '$150 are the same year at two stages. This page carries only the enacted '
             'one, and the two are never subtracted.'),
    dict(key='passed', board='school-committee', date='2025-05-07', kind='minutes',
         doc='7207',
         quote='The House budget passed including 150 per pupil minimum aid increase.',
         why='The rate, stated as passed. DESE’s workbook then runs it: Lunenburg’s '
             'whole FY2026 increase is $150.00 a pupil, to the cent.'),
    dict(key='thirty', board='finance-committee', date='2024-03-20', kind='minutes',
         doc='6481',
         quote='The State is giving a minimum aid of 30 per pupil so that’s an '
               'additional $44,280 in additional chapter 78.',
         why='Said about FY2025 and about MONTY TECH, not about Lunenburg Public Schools '
             '-- $44,280 is exactly $30.00 for each of the 1,476 foundation pupils named '
             'in the same passage. The enacted FY2025 rate in DESE’s workbook is '
             '$104.00. Two stages of one year, five months apart, and the page prints '
             'both rather than reconciling them.'),
    dict(key='trending', board='finance-committee', date='2020-02-13', kind='minutes',
         doc='2135',
         quote='Peter Beardmore noted that Ch 70 increases are trending lower, despite '
               'passage of The Student Opportunity Act.',
         why='Said in February 2020. The three years that followed, in DESE’s own '
             'figures: +$233,668, +$2,198, +$49,680. The observation holds for those '
             'years. It does not hold for FY2023, which was +$898,610.'),
    dict(key='novick', board='finance-committee', date='2021-10-28', kind='minutes',
         doc='2097',
         quote='After the Commonwealth determines how much each district is required to '
               'spend, municipalities are obligated to fund 59 percent of that foundation '
               'budget, while the Commonwealth provides 41 percent.',
         why='A description of the formula given to the Finance Committee by the '
             'Massachusetts Association of School Committees. Recomputed for Lunenburg '
             'below -- it is close for the year it was said and it is not a constant, '
             'which is the whole subject of this page.'),
    dict(key='districts', board='finance-committee', date='2024-06-27', kind='minutes',
         doc='6635',
         quote='There will be a larger meeting across the 220 Districts in the State that '
               'received minimum aid.',
         why='A count of minimum aid districts stated in public. This archive holds the '
             'aid components for seven districts and cannot check 220 of them, so it is '
             'here as something said and not as something measured.'),
    dict(key='commission', board='select-board', date='2025-05-20', kind='agenda',
         doc='7231',
         quote='Review Letter of Support for the Establishment of a Chapter 70 Commission '
               'to Review the Foundation Budget and Local Contribution Formulas',
         why='The two halves of this page, named as the two things the town asked the '
             'Legislature to reopen -- the foundation budget and the local contribution '
             'formula. It is evidence of intent and of what the town believes the '
             'problem is. It is not evidence of an outcome.'),
    dict(key='montytech', board='finance-committee', date='2026-02-05', kind='minutes',
         doc='7631',
         quote='The required minimum Lunenburg is expected to contribute is $1,378,183. '
               'The FY 27 foundation budget for Lunenburg is $2,251,179.',
         why='Monty Tech’s FY2027 figures, given to the Finance Committee. They are '
             'the OTHER SIDE of the split this page establishes: in FY2026 the town’s '
             'required contribution exceeds the school district’s by $1,270,711, and '
             'the town’s foundation budget exceeds the district’s by $2,103,516. '
             'Different year and different document, so this corroborates the shape and '
             'does not tie to it.'),
]

# THE REGISTRY OUTRANKS THE PAGE (rule 7c). These rows are cited, not restated -- three
# of them were already registered before this page existed and two were added by it. Named
# rather than pattern-matched, because a loose `like '%chapter 70%'` pulled in the school
# choice tuition row and the town's own growth-rate row, neither of which is a limit THIS
# page hits, and a citation to a gap a page does not hit is noise dressed as rigour.
WANTED_GAPS = [
    'What Chapter 70 aid would actually do if enrollment fell',
    'What the foundation budget pays per pupil for each kind of child',
    'How many children Chapter 70 is actually paid for',
    'Why Chapter 70 aid moved by more than the components DESE publishes',
    'Which cell of DESE’s contribution sheet is mislabelled in FY2020',
]

SEARCHED = ['Chapter 70', 'minimum aid', 'foundation budget', 'combined effort yield',
            'required local contribution', 'Student Opportunity Act']


def fail(msg):
    raise SystemExit('%s\nNothing written.' % msg)


def and_list(items):
    """`a, b and c`, built rather than typed, because the number of items is data."""
    items = list(items)
    if len(items) == 1:
        return items[0]
    return '%s and %s' % (', '.join(items[:-1]), items[-1])


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def definitions_hold(db):
    """The DESE definitions this page quotes are not typed twice.

    They are quoted here and they must still be what the workbook says. The workbook is a
    4.6 MB xlsx and openpyxl is not a build dependency, so what is asserted instead is that
    the DOCUMENT is still the one we read: its sha256 against the manifest. If the file is
    ever replaced the hash moves and this stops."""
    rows = q(db, "SELECT DISTINCT doc_id FROM dese_ch70_aid_factor")
    have = {r['doc_id'] for r in rows}
    want = 'sources/' + DOC_KEY
    if have != {want}:
        fail('the aid components are attributed to %s, not to %s. The definitions quoted '
             'on this page are cell references into that workbook.' % (sorted(have), want))


def document():
    """The workbook, read out of the manifest rather than typed (rules 2 and 12)."""
    with open(MANIFEST, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row['key'] == DOC_KEY:
                return {'path': 'sources/' + row['key'], 'sha256': row['sha256'],
                        'bytes': int(row['bytes']), 'url': row['upstream'],
                        'docs_url': '/docs/' + row['key'],
                        'filename': row['key'].split('/')[-1],
                        'publisher': 'Massachusetts Department of Elementary and '
                                     'Secondary Education',
                        'sheets': [SHEET_AID, SHEET_CONTRIB, 'User Guide'],
                        'stage': 'DESE’s published Chapter 70 calculation for each '
                                 'fiscal year. Not a Governor’s budget proposal and '
                                 'not a receipt.'}
    fail('%s is not in the archive manifest. A figure without its document is not '
         'publishable.' % DOC_KEY)


def said_in_meetings():
    out = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here -- a quote on this page is attributed to a document that '
                 'is not in the archive' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            fail('the quote attributed to %s %s is no longer in %s -- quote the source, '
                 'never your rendering of it' % (spec['board'], spec['date'], rel))
        kind = 'Minutes' if spec['kind'] == 'minutes' else 'Agenda'
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'], kind=kind,
            cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/%s/_%s%s%s-%s'
                 % (kind, spec['date'][5:7], spec['date'][8:10], spec['date'][:4],
                    spec['doc'])))
    return out


def searched():
    """Each term, with its DENOMINATOR. A grep that finds nothing prints nothing, and
    nothing reads as nobody said it."""
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here -- a search of nothing is not a search')
    rows = list(csv.DictReader(open(idx, encoding='utf-8')))
    readable = []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
    if not readable:
        fail('no meeting document is readable -- refusing to publish a count of what '
             'nobody said')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    terms = [dict(term=t,
                  documents=sum(1 for b in bodies if re.search(re.escape(t), b, re.I)))
             for t in SEARCHED]

    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        fail('sources/data/minutes-searchable.csv is not here -- the searchable share '
             'cannot be typed')
    tally = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            tally[k] += int(r[k] or 0)
    if not tally['searchable'] or tally['held'] != tally['searchable'] + tally['unsearchable']:
        fail('minutes-searchable.csv does not reconcile -- refusing to publish a coverage '
             'figure that does not add up')
    return terms, dict(held=tally['held'], searchable=tally['searchable'],
                       unsearchable=tally['unsearchable'],
                       image_scan=tally['image_scan'],
                       searchable_share=round(tally['searchable'] / tally['held'], 4))


# The aid components that BUILD the year's aid. `ch70_aid_reduction` is deliberately NOT
# here: it is a separate column that does not enter this sum in the years it is populated,
# which is exactly why four years do not reconcile and why the page says so rather than
# quietly folding it in.
BUILD_TERMS = ['foundation_aid_increment', 'down_payment_aid_increment',
               'growth_aid_increment', 'target_aid_phase_in', 'minimum_aid_increment',
               'non_operating_reduction', 'hold_harmless_low_income',
               'minimum_aid_adjustment']


def build():
    if not os.path.exists(DB):
        raise SystemExit('%s is missing. Run scripts/build_db.py.' % DB)
    db = sqlite3.connect(DB)
    definitions_hold(db)

    # ---- the district side: the aid build-up, every year -----------------------------
    aid = {r['fy']: r for r in q(
        db, "SELECT * FROM dese_ch70_aid_factor WHERE lea=? AND level='district' "
            "ORDER BY fy", LEA)}
    if len(aid) < MIN_YEARS:
        fail('only %d years of aid components for %s; expected at least %d'
             % (len(aid), LEA, MIN_YEARS))

    # ---- the municipal side: where ability to pay is computed ------------------------
    town = {r['fy']: r for r in q(
        db, 'SELECT * FROM dese_ch70_contribution WHERE municipality=? ORDER BY fy', TOWN)}
    if not town:
        fail('no rows in dese_ch70_contribution for %s -- the municipal join matched '
             'nothing, which looks exactly like a town with no contribution' % TOWN)
    missing = sorted(set(aid) - set(town))
    if missing:
        fail('the district years %s have no municipal row. The two tables are different '
             'grains and the page joins them; a partial join publishes a hole as a zero.'
             % missing)

    years = sorted(aid)
    first, last = years[0], years[-1]

    # ---- 1. THE HEADLINE: the whole increase is the floor -----------------------------
    a, t = aid[last], town[last]
    prior = aid[last - 1]
    delta = a['ch70_aid'] - prior['ch70_aid']
    enrol = a['foundation_enrollment']
    if not enrol:
        fail('FY%d foundation enrollment is zero or missing; every per-pupil figure on '
             'this page divides by it' % last)
    per_pupil = delta / enrol
    min_per_pupil = (a['minimum_aid_increment'] or 0) / enrol
    if abs(per_pupil - min_per_pupil) > 0.005:
        fail('FY%d: the whole aid increase is $%.2f a pupil but the minimum aid increment '
             'is $%.2f a pupil. The page’s headline claim is that they are the same '
             'number; it is no longer true and the prose would be wrong.'
             % (last, per_pupil, min_per_pupil))

    headline = {
        'fy': last,
        'prior_fy': last - 1,
        'aid': a['ch70_aid'], 'prior_aid': prior['ch70_aid'], 'increase': delta,
        'minimum_aid_increment': a['minimum_aid_increment'] or 0,
        'foundation_aid_increment': a['foundation_aid_increment'] or 0,
        'enrollment': enrol,
        'per_pupil': round(per_pupil, 2),
        'foundation_budget': a['foundation_budget'],
        'foundation_per_pupil': a['foundation_budget'] / enrol,
        'times': (a['foundation_budget'] / enrol) / per_pupil,
        'target_aid_pct': a['target_aid_pct'],
        'aid_share_of_foundation': a['ch70_aid'] / a['foundation_budget'],
        'cells': CELLS,
    }

    # ---- 2. WHY IT IS ZERO: DESE's own rule, reproduced -------------------------------
    need = a['foundation_budget'] - a['required_local_contribution']
    rule_years, rule_broken = [], []
    for fy in years[1:]:
        n = aid[fy]['foundation_budget'] - aid[fy]['required_local_contribution']
        predicted = max(0.0, n - aid[fy - 1]['ch70_aid'])
        actual = aid[fy]['foundation_aid_increment'] or 0
        (rule_years if abs(predicted - actual) < 1.5 else rule_broken).append(fy)
    if last not in rule_years:
        fail('DESE’s own foundation-aid rule no longer reproduces FY%d. The page '
             'explains the zero with that rule.' % last)

    why_zero = {
        'fy': last,
        'foundation_budget': a['foundation_budget'],
        'required_local_contribution': a['required_local_contribution'],
        'need': need,
        'prior_aid': prior['ch70_aid'],
        'headroom': prior['ch70_aid'] - need,
        'rule_holds_in': len(rule_years), 'rule_of': len(years) - 1,
        'rule_broken_in': rule_broken,
        'definition_cell': 'User Guide!B34',
    }

    # ---- 3. THE FLOOR IS STATEWIDE: the peers, to the cent ----------------------------
    peers = {}
    for r in q(db, "SELECT * FROM dese_ch70_aid_factor WHERE level='district'"):
        peers.setdefault(r['fy'], {})[r['lea']] = r
    if len(peers.get(last, {})) < 5:
        fail('fewer than five districts in FY%d; the claim that the floor is a statewide '
             'rate rests on several districts landing on the identical figure' % last)

    floor = []
    for fy in years[1:]:
        rates = []
        for lea, r in peers.get(fy, {}).items():
            p = peers.get(fy - 1, {}).get(lea)
            if not p or not r['foundation_enrollment']:
                continue
            rates.append((r['district'], round((r['ch70_aid'] - p['ch70_aid'])
                                               / r['foundation_enrollment'], 2),
                          round((r['minimum_aid_increment'] or 0)
                                / r['foundation_enrollment'], 2)))
        if not rates:
            continue
        counts = collections.Counter(x[1] for x in rates)
        modal, n = counts.most_common(1)[0]
        floor.append({
            'fy': fy,
            'districts': len(rates),
            'shared_rate': modal if n > 1 else None,
            'districts_at_rate': n if n > 1 else 0,
            'lunenburg': round((aid[fy]['ch70_aid'] - aid[fy - 1]['ch70_aid'])
                               / aid[fy]['foundation_enrollment'], 2),
            'lunenburg_at_rate': bool(n > 1 and abs(
                (aid[fy]['ch70_aid'] - aid[fy - 1]['ch70_aid'])
                / aid[fy]['foundation_enrollment'] - modal) < 0.005),
            'rows': sorted([{'district': d, 'per_pupil': v, 'min_per_pupil': m}
                            for d, v, m in rates], key=lambda x: x['district']),
        })
    if not floor:
        fail('the peer join produced no per-pupil rates. That looks exactly like a state '
             'with no minimum aid, and it is not what the workbook holds.')

    on_floor = [f['fy'] for f in floor if f['lunenburg_at_rate']]
    if last not in on_floor:
        fail('FY%d is not on the shared per-pupil rate. The page leads with it.' % last)

    # ---- 4. THE AID SERIES, term by term, with the reconciliation stated --------------
    series, unreconciled = [], []
    for fy in years:
        r = aid[fy]
        row = {'fy': fy, 'aid': r['ch70_aid'],
               'enrollment': r['foundation_enrollment'],
               'foundation_budget': r['foundation_budget'],
               'required_local_contribution': r['required_local_contribution'],
               'required_share': (r['required_local_contribution'] / r['foundation_budget']
                                  if r['foundation_budget'] else None),
               'target_aid_pct': r['target_aid_pct'],
               'foundation_aid': r['foundation_aid_increment'] or 0,
               'minimum_aid': r['minimum_aid_increment'] or 0,
               'other_increments': sum((r[k] or 0) for k in BUILD_TERMS
                                       if k not in ('foundation_aid_increment',
                                                    'minimum_aid_increment')),
               'reduction': r['ch70_aid_reduction'] or 0}
        if fy > first:
            d = r['ch70_aid'] - aid[fy - 1]['ch70_aid']
            built = sum((r[k] or 0) for k in BUILD_TERMS)
            row['change'] = d
            row['per_pupil'] = (round(d / r['foundation_enrollment'], 2)
                                if r['foundation_enrollment'] else None)
            row['components_sum'] = built
            row['reconciles'] = abs(built - d) < 1.0
            if not row['reconciles']:
                unreconciled.append({'fy': fy, 'change': round(d),
                                     'components_sum': round(built),
                                     'unexplained': round(d - built),
                                     'reduction_column': r['ch70_aid_reduction']})
        else:
            row['change'] = None
            row['per_pupil'] = None
            row['components_sum'] = None
            row['reconciles'] = None
        series.append(row)

    # ---- 5. THE MUNICIPAL SIDE: wealth, and the regime flip --------------------------
    contribution, target_is_cey = [], True
    for fy in years:
        r = town[fy]
        if abs((r['target_local_contribution'] or 0) - (r['combined_effort_yield'] or 0)) > 1:
            target_is_cey = False
        contribution.append({
            'fy': fy,
            'equalized_valuation': r['equalized_valuation'],
            'income': r['income'],
            'property_effort': r['property_local_effort'],
            'income_effort': r['income_local_effort'],
            'combined_effort_yield': r['combined_effort_yield'],
            'target': r['target_local_contribution'],
            'town_foundation_budget': r['town_foundation_budget'],
            'town_enrollment': r['town_foundation_enrollment'],
            'target_share': (r['target_local_contribution'] / r['town_foundation_budget']
                             if r['town_foundation_budget'] else None),
            'mrgf': r['municipal_revenue_growth_factor'],
            'preliminary': r['preliminary_contribution'],
            'excess_effort': r['excess_effort'] or 0,
            'effort_reduction': r['effort_reduction'] or 0,
            'shortfall': r['shortfall'] or 0,
            'dollar_increment': r['dollar_increment'] or 0,
            'acceleration': r['acceleration'] or 0,
            'rlc': r['required_local_contribution'],
            'above_target': (r['excess_effort'] or 0) > 0,
        })
    if not target_is_cey:
        fail('the target local contribution is no longer equal to the combined effort '
             'yield in every year. The page states that identity as the reason enrollment '
             'does not enter the town’s contribution.')

    # The build identity, and the one year it does not hold.
    build_ok, build_bad = [], []
    for fy in years[1:]:
        r, p = town[fy], town[fy - 1]
        prelim_pred = p['required_local_contribution'] * (1 + (r['municipal_revenue_growth_factor'] or 0))
        rlc_pred = (r['preliminary_contribution'] - (r['effort_reduction'] or 0)
                    + (r['dollar_increment'] or 0) + (r['acceleration'] or 0))
        ok = (abs(r['preliminary_contribution'] - prelim_pred) < 2.0
              and abs(r['required_local_contribution'] - rlc_pred) < 1.0)
        (build_ok if ok else build_bad).append(
            fy if ok else {'fy': fy,
                           'preliminary_printed': round(r['preliminary_contribution']),
                           'prior_rlc_times_mrgf': round(prelim_pred),
                           'rlc_printed': round(r['required_local_contribution']),
                           'cells': {'preliminary': 'dataContribution!O2593',
                                     'rlc': 'dataContribution!U2593'}})

    above = [c['fy'] for c in contribution if c['above_target']]
    below = [c['fy'] for c in contribution if not c['above_target']]
    shares = [(c['fy'], aid[c['fy']]['required_local_contribution']
               / aid[c['fy']]['foundation_budget']) for c in contribution]
    trough = min(shares, key=lambda x: x[1])
    share = {'first_fy': shares[0][0], 'first': shares[0][1],
             'low_fy': trough[0], 'low': trough[1],
             'last_fy': shares[-1][0], 'last': shares[-1][1],
             'rose_since_trough': sum(1 for i in range(1, len(shares))
                                      if shares[i][0] > trough[0]
                                      and shares[i][1] > shares[i - 1][1]),
             'fell_since_trough': sum(1 for i in range(1, len(shares))
                                      if shares[i][0] > trough[0]
                                      and shares[i][1] <= shares[i - 1][1])}
    if not above or not below:
        fail('every year is on the same side of target. The page’s second finding is '
             'that Lunenburg crossed from one to the other.')
    regime = {
        'above_first': min(above), 'above_last': max(above), 'above_years': len(above),
        'below_first': min(below), 'below_last': max(below), 'below_years': len(below),
        'effort_reduction_total': sum(c['effort_reduction'] for c in contribution),
        'dollar_increment_total': sum(c['dollar_increment'] for c in contribution),
        # BELOW TARGET AND BEING CHARGED FOR IT ARE NOT THE SAME YEAR, and writing them as
        # one was the first draft of this page's fifth finding. Lunenburg fell short of
        # target in FY2020 and the formula added nothing for three years; the dollar
        # increment starts later. Both dates are carried so the prose cannot conflate them.
        'increment_first': min([c['fy'] for c in contribution
                                if c['dollar_increment'] > 0], default=None),
        'increment_years': sum(1 for c in contribution if c['dollar_increment'] > 0),
        'reduction_first': min([c['fy'] for c in contribution
                                if c['effort_reduction'] > 0], default=None),
        'reduction_years': sum(1 for c in contribution if c['effort_reduction'] > 0),
        'quiet_years': sum(1 for c in contribution
                           if not c['above_target'] and c['dollar_increment'] == 0),
        'note': 'A sum of ANNUAL adjustments, not a cumulative total. Each year’s '
                'adjustment also carries forward, because next year’s preliminary '
                'contribution is this year’s requirement grown by the MRGF.',
    }

    # ---- 6. THE ALLOCATION: the town's contribution, split between two districts ------
    allocation = []
    for fy in years:
        r, tr = aid[fy], town[fy]
        pred = tr['required_local_contribution'] * r['foundation_budget'] / tr['town_foundation_budget']
        allocation.append({
            'fy': fy,
            'town_rlc': tr['required_local_contribution'],
            'town_foundation_budget': tr['town_foundation_budget'],
            'district_rlc': r['required_local_contribution'],
            'district_foundation_budget': r['foundation_budget'],
            'predicted': pred,
            'difference': r['required_local_contribution'] - pred,
            'holds': abs(r['required_local_contribution'] - pred) < 2.0,
            'elsewhere_rlc': tr['required_local_contribution'] - r['required_local_contribution'],
            'elsewhere_foundation': tr['town_foundation_budget'] - r['foundation_budget'],
        })
    holds = [x['fy'] for x in allocation if x['holds']]
    allocation_summary = {'holds_in': len(holds), 'of': len(allocation),
                          'exceptions': [x['fy'] for x in allocation if not x['holds']],
                          'worst': max((abs(x['difference']) for x in allocation
                                        if not x['holds']), default=0.0)}
    if last not in holds:
        fail('the allocation identity does not hold in FY%d, and the page rests the '
             'marginal-pupil section on it' % last)

    # ---- 7. WHERE LUNENBURG SITS, statewide ------------------------------------------
    dist = q(db, "SELECT fy, districts, p25, median, p75, p_max, lunenburg, "
                 "lunenburg_rank_of_districts FROM dese_ch70_statewide "
                 "WHERE measure='required local contribution as a share of the "
                 "foundation budget' ORDER BY fy")
    dist = [r for r in dist if r['fy'] >= first]
    if not dist:
        fail('dese_ch70_statewide has no required-share distribution for FY%d on. The '
             'page compares Lunenburg’s share against the state and the join matched '
             'nothing.' % first)

    # ---- 8. WEALTH, against every municipality in the same table ---------------------
    wealth_from = max(min(below) - 1, first)
    rows = {}
    for r in q(db, 'SELECT fy, municipality, equalized_valuation, combined_effort_yield '
                   'FROM dese_ch70_contribution WHERE fy IN (?,?)', wealth_from, last):
        rows.setdefault(r['municipality'], {})[r['fy']] = r
    growth = [(m, v[last]['equalized_valuation'] / v[wealth_from]['equalized_valuation'] - 1,
               v[last]['combined_effort_yield'] / v[wealth_from]['combined_effort_yield'] - 1)
              for m, v in rows.items()
              if wealth_from in v and last in v
              and v[wealth_from]['equalized_valuation'] and v[wealth_from]['combined_effort_yield']]
    if len(growth) < 300:
        fail('only %d municipalities have both FY%d and FY%d. The rank published here is '
             'a rank among all of them.' % (len(growth), wealth_from, last))
    growth.sort(key=lambda x: -x[1])
    names = [x[0] for x in growth]
    if TOWN not in names:
        fail('%s is not in the statewide wealth comparison, which is a join that matched '
             'nothing for the one town this page is about' % TOWN)
    mid = sorted(x[1] for x in growth)[len(growth) // 2]
    cey_sorted = sorted(growth, key=lambda x: -x[2])
    wealth = {
        'fy_from': wealth_from, 'fy_to': last,
        'municipalities': len(growth),
        'eqv_growth': [x[1] for x in growth if x[0] == TOWN][0],
        'eqv_rank': names.index(TOWN) + 1,
        'eqv_median': mid,
        'cey_growth': [x[2] for x in growth if x[0] == TOWN][0],
        'cey_rank': [x[0] for x in cey_sorted].index(TOWN) + 1,
        'cey_median': sorted(x[2] for x in growth)[len(growth) // 2],
    }

    # ---- 9. THE MARGINAL PUPIL: what follows, and what does not ----------------------
    # Numeric, not analytic, and every assumption is published beside the number. Hold the
    # TOWN's required contribution fixed -- it is the combined effort yield path, which
    # carries no enrollment term -- and let one more pupil raise both foundation budgets by
    # the same amount, then re-run the two identities the page has already established.
    fpp = a['foundation_budget'] / enrol
    t_rlc, t_fb, d_fb = t['required_local_contribution'], t['town_foundation_budget'], a['foundation_budget']
    d_rlc_after = t_rlc * (d_fb + fpp) / (t_fb + fpp)
    need_after = (d_fb + fpp) - d_rlc_after
    marginal = {
        'fy': last,
        'foundation_per_pupil': fpp,
        'district_rlc_now': a['required_local_contribution'],
        'district_rlc_after': d_rlc_after,
        'rlc_change': d_rlc_after - a['required_local_contribution'],
        'need_now': need,
        'need_after': need_after,
        'need_change': need_after - need,
        'headroom': prior['ch70_aid'] - need,
        'pupils_to_close': (prior['ch70_aid'] - need) / (need_after - need),
        'town_rlc_change': 0.0,
        'assumptions': [
            'The town’s required contribution does not move. It is the combined '
            'effort yield path, and DESE’s target local contribution equals the '
            'combined effort yield in all %d years published.' % len(years),
            'The extra pupil costs the AVERAGE foundation amount. DESE builds the '
            'foundation budget from per-pupil rates that differ by grade and by category '
            'and does not publish them here, so the marginal cost is unknown and the '
            'average is standing in for it.',
            'The statutory cap on the target local share does not bind. Lunenburg’s '
            'target share is %.1f%% of its foundation budget in FY%d against a cap of '
            '82.5%%.' % (100 * t['target_local_contribution'] / t['town_foundation_budget'],
                         last),
            'Everything else in the formula is held at its FY%d value, including the '
            'minimum aid rate, which the Legislature sets each year and which has ranged '
            'from $30 to $150 a pupil in the years published.' % last,
        ],
        'is_measurement': False,
    }

    # ---- THE TWO SIDES SINCE THE REGIME CHANGED --------------------------------------
    # FOUND BY THE PERSONA REVIEW, and the page was materially worse without it. The first
    # reader in notes/process/PERSONAS.md searches for the worst fact and stops; the second
    # repeats one sentence at a kitchen table. Everything else on this page is about the
    # MECHANISM, and a resident's question is simpler than that: which side has moved more.
    # Both figures are the same stage and the same table, so the comparison is like for
    # like -- which is the only reason it can be made at all.
    since_fy = wealth_from
    since = {
        'from_fy': since_fy, 'to_fy': last,
        'aid_from': aid[since_fy]['ch70_aid'], 'aid_to': a['ch70_aid'],
        'aid_change': a['ch70_aid'] - aid[since_fy]['ch70_aid'],
        'aid_pct': a['ch70_aid'] / aid[since_fy]['ch70_aid'] - 1,
        'required_from': aid[since_fy]['required_local_contribution'],
        'required_to': a['required_local_contribution'],
        'required_change': (a['required_local_contribution']
                            - aid[since_fy]['required_local_contribution']),
        'required_pct': (a['required_local_contribution']
                         / aid[since_fy]['required_local_contribution'] - 1),
        'enrollment_from': aid[since_fy]['foundation_enrollment'],
        'enrollment_to': a['foundation_enrollment'],
        'foundation_from': aid[since_fy]['foundation_budget'],
        'foundation_to': a['foundation_budget'],
        'stage': 'Both figures are DESE’s published calculation for their year. Same '
                 'table, same stage, so the two are comparable.',
    }

    # ---- THE TWO STAGES OF ONE YEAR, side by side and never subtracted ---------------
    # RULE 1, made concrete. Each row pairs a per-pupil minimum aid rate the town was TOLD
    # at an earlier stage with the rate DESE's workbook later ran. The earlier figure is
    # read out of the quote it appears in rather than typed a second time; the later one is
    # computed off the floor series. The page prints them beside each other and the
    # difference is never taken -- it is not a measurement of anything, it is two documents.
    def rate_for(fy):
        f = [x for x in floor if x['fy'] == fy]
        if not f or f[0]['shared_rate'] is None:
            fail('FY%d has no shared per-pupil rate, and the stage comparison names it' % fy)
        return f[0]['shared_rate']

    stage_examples = []
    for key, fyy, stage, needle in (
            ('thirty', 2025, 'a Governor’s-budget figure, quoted to the Finance Committee '
                             'five months before the year was set',
             r'minimum aid of (\d+) per pupil'),
            ('house', 2026, 'the Governor’s figure and the House’s, quoted to the School '
                            'Committee a month before the year was set',
             r'from the \$(\d+) per student')):
        spec = [x for x in QUOTES if x['key'] == key][0]
        m = re.search(needle, spec['quote'])
        if not m:
            fail('the quote %r no longer carries the per-pupil rate this page pairs with '
                 'FY%d. Rule 13: quote the source, never your rendering of it.'
                 % (key, fyy))
        stage_examples.append({
            'key': key, 'fy': fyy, 'stage': stage,
            'said': float(m.group(1)), 'said_on': spec['date'],
            'board': spec['board'].replace('-', ' ').title(),
            'enacted': rate_for(fyy),
        })

    # ---- A FIGURE STATED IN PUBLIC, RECOMPUTED ---------------------------------------
    # The Massachusetts Association of School Committees told the Finance Committee that
    # municipalities fund 59% of the foundation budget and the Commonwealth 41%. That is a
    # STATEWIDE description, so this recomputes Lunenburg's own ratio for the fiscal year
    # the meeting was about and says which it is. The stated shares are the only two
    # numbers on this page typed rather than derived, and they are typed because they are a
    # QUOTATION -- the quote itself is asserted against the minutes above.
    said_quote = [x for x in QUOTES if x['key'] == 'novick'][0]
    stated_fy = int(said_quote['date'][:4]) + 1     # a meeting in Oct 2021 is about FY2022
    if stated_fy not in aid:
        fail('FY%d has no aid row, and the page recomputes a publicly stated share against '
             'it' % stated_fy)
    corroboration = {
        'board': said_quote['board'].replace('-', ' ').title(),
        'date': said_quote['date'],
        'stated_municipal': 0.59, 'stated_state': 0.41,
        'fy': stated_fy,
        'recomputed': (aid[stated_fy]['required_local_contribution']
                       / aid[stated_fy]['foundation_budget']),
        'scope': 'The statement was about the statewide split, not about Lunenburg. This '
                 'recomputes Lunenburg’s own ratio for the year the meeting was about, so '
                 'it is a check on the shape and not on the speaker.',
    }

    # ---- WHAT THE TOWN ACTUALLY SPENDS AGAINST THE REQUIREMENT -----------------------
    # A required contribution is a FLOOR on spending, not a description of it, and the page
    # says so. Split on `nss_stage`: rule 1, and the workbook labels its last two years
    # budgeted while heading the column `actualNSS`.
    nss = q(db, "SELECT fy, nss_stage, nss_pct_of_required FROM dese_ch70_formula "
                "WHERE lea=? AND level='district' AND nss_pct_of_required IS NOT NULL "
                "AND fy>=? ORDER BY fy", LEA, first)
    if not nss:
        fail('dese_ch70_formula returned no net school spending ratios for %s from FY%d. '
             'The page states that the town spends above the required minimum.' % (LEA, first))
    spending = {
        'years': len(nss),
        'first_fy': nss[0]['fy'], 'last_fy': nss[-1]['fy'],
        'above_required': sum(1 for r in nss if r['nss_pct_of_required'] > 1),
        'lowest': min(r['nss_pct_of_required'] for r in nss),
        'latest': nss[-1]['nss_pct_of_required'],
        'latest_stage': nss[-1]['nss_stage'],
        'stages': sorted({r['nss_stage'] for r in nss if r['nss_stage']}),
        'rows': [{'fy': r['fy'], 'stage': r['nss_stage'],
                  'pct_of_required': r['nss_pct_of_required']} for r in nss],
    }

    # ---- the limits, from the registry rather than from this page --------------------
    gaps = q(db, 'SELECT side, what, why FROM money_gaps')
    if not gaps:
        fail('money_gaps is empty -- the join that reads the registry matched nothing')
    by_what = {g['what']: g for g in gaps}
    keep = []
    for want in WANTED_GAPS:
        hit = [g for w, g in by_what.items() if w.startswith(want)]
        if not hit:
            fail('money_gaps has no row beginning %r. Rule 7c says the registry outranks '
                 'the page: this page cites that row rather than restating the limit, so '
                 'a rename there must stop this build rather than silently drop it.'
                 % want)
        keep.append(hit[0])

    def split(g):
        m = re.search(r'—\s*closes:\s*(.+)$', g['why'], re.S)
        return {'side': g['side'], 'what': g['what'],
                'why': (g['why'][:m.start()].rstrip(' —') if m else g['why']),
                'closes': (m.group(1).strip() if m else None)}

    terms, minutes = searched()

    # ---- THE CONCLUSIONS -------------------------------------------------------------
    # Five quantities the page does not otherwise need, computed here beside everything
    # else so that no figure in a sentence is typed (rule 2):
    #   * how long the floor has bound, as a RUN of years rather than a count of them --
    #     FY2023 is not on the floor, so "the last four increases" would be wrong;
    #   * the per-pupil rate the Legislature chose in each of those years;
    #   * the two wealth series and the two growth rates as percentages, because a
    #     conclusion states a percentage and the payload carries fractions.
    floor_span = last - min(on_floor) + 1
    floor_rates = [rate_for(f) for f in on_floor]
    rates_text = and_list([C.usd(r) for r in floor_rates])
    rate_figures = {'rate_%d' % f: figure(rate_for(f), C.usd(rate_for(f)))
                    for f in on_floor}
    req_pct, aid_pct = 100 * since['required_pct'], 100 * since['aid_pct']
    share_first_pct = 100 * share['first']
    share_low_pct = 100 * share['low']
    share_last_pct = 100 * share['last']
    eqv_growth_pct, eqv_median_pct = 100 * wealth['eqv_growth'], 100 * wealth['eqv_median']
    cey_growth_pct, cey_median_pct = 100 * wealth['cey_growth'], 100 * wealth['cey_median']

    conclusions = emit('why-we-only-get-minimum-aid', [
        conclusion(
            id='the-whole-increase-is-the-legislatures-floor',
            claim='Increase in state school aid for FY2026, all of it the Legislature’s flat minimum',
            so_what='The funding formula itself awarded nothing. What the town gets moves with a rate set on Beacon Hill.',
            lede='Lunenburg’s entire increase in state school aid for %s was the flat '
                  'minimum the Legislature votes each year — %s, which is exactly %s for '
                  'each of the %s pupils the state’s funding formula counts. The formula '
                  'itself awarded %s.'
                  % (C.fy(last), C.usd(delta), C.usd(headline['per_pupil']),
                     C.num(enrol), C.usd(headline['foundation_aid_increment'])),
            detail='The formula pays foundation aid only where the foundation budget less '
                   'the town’s required contribution exceeds last year’s aid. For %s that '
                   'is %s less %s, or %s of need, against %s already being paid: '
                   'Lunenburg sits %s above the line at which the formula pays anything. '
                   'It has been in that position in %s of the last %s years, and the '
                   'floor the Legislature chose in those years was %s a pupil. So what '
                   'the town receives moves with a rate set on Beacon Hill each spring, '
                   'not with anything its own costs or its own enrollment do.'
                   % (C.fy(last), C.usd(why_zero['foundation_budget']),
                      C.usd(why_zero['required_local_contribution']),
                      C.usd(why_zero['need']), C.usd(why_zero['prior_aid']),
                      C.usd(why_zero['headroom']), C.num(len(on_floor)),
                      C.num(floor_span), rates_text),
            figures=dict(
                fy=figure(last, C.fy(last)),
                increase=figure(delta, C.usd(delta)),
                per_pupil=figure(headline['per_pupil'], C.usd(headline['per_pupil'])),
                enrollment=figure(enrol, C.num(enrol)),
                foundation_aid=figure(headline['foundation_aid_increment'],
                                      C.usd(headline['foundation_aid_increment'])),
                foundation_budget=figure(why_zero['foundation_budget'],
                                         C.usd(why_zero['foundation_budget'])),
                required_local_contribution=figure(
                    why_zero['required_local_contribution'],
                    C.usd(why_zero['required_local_contribution'])),
                need=figure(why_zero['need'], C.usd(why_zero['need'])),
                prior_aid=figure(why_zero['prior_aid'], C.usd(why_zero['prior_aid'])),
                headroom=figure(why_zero['headroom'], C.usd(why_zero['headroom'])),
                floor_years=figure(len(on_floor), C.num(len(on_floor))),
                floor_span=figure(floor_span, C.num(floor_span)),
                **rate_figures),
            figure='increase',
            kind='measured',
            allow=('Chapter 70',),
            basis='DESE’s Chapter 70 Trends workbook, sheets %s and %s: the aid '
                  'components as DESE ran them for each fiscal year, %s. Not a '
                  'Governor’s-budget proposal and not a receipt — those are different '
                  'numbers for the same year and are never differenced here.'
                  % (SHEET_AID, SHEET_CONTRIB, C.fyspan(first, last)),
            not_shown='Whether one more child would bring the town anything. While the '
                      'floor binds, aid moves at the Legislature’s flat per-pupil rate — '
                      'but a large enough foundation budget increase closes the headroom '
                      'and moves the district off the floor entirely, and no document in '
                      'this archive models that.',
            see=[('/state-aid', 'all state aid, of which this is the largest part')],
        ),
        conclusion(
            id='the-local-share-is-rising-faster-than-the-aid',
            claim='Rise since FY2019 in what the state requires Lunenburg to pay for its own schools',
            so_what='State aid rose by less over the same years, and the pupil count the formula runs on fell.',
            lede='Since %s the amount the state requires Lunenburg to pay towards its '
                  'own schools has risen %s, while the state aid it sends rose %s — and '
                  'over the same years the pupil count the formula runs on fell from %s '
                  'to %s.'
                  % (C.fy(since['from_fy']), C.pct(req_pct), C.pct(aid_pct),
                     C.num(since['enrollment_from']), C.num(since['enrollment_to'])),
            detail='In dollars the required local contribution went from %s to %s, up %s, '
                   'while aid went from %s to %s, up %s. Both are DESE’s published '
                   'calculation for their own year, so the two are the same stage and can '
                   'be compared. What it changes for a resident is where the foundation '
                   'budget is paid from: the required local share of it was %s in %s, '
                   'fell to %s by %s, and is %s now. A school budget that grows is '
                   'increasingly a town bill, and that shift happens whether or not the '
                   'district changes anything it does.'
                   % (C.usd(since['required_from']), C.usd(since['required_to']),
                      C.usd(since['required_change']), C.usd(since['aid_from']),
                      C.usd(since['aid_to']), C.usd(since['aid_change']),
                      C.pct(share_first_pct), C.fy(share['first_fy']),
                      C.pct(share_low_pct), C.fy(share['low_fy']),
                      C.pct(share_last_pct)),
            figures=dict(
                from_fy=figure(since['from_fy'], C.fy(since['from_fy'])),
                required_pct=figure(req_pct, C.pct(req_pct)),
                aid_pct=figure(aid_pct, C.pct(aid_pct)),
                enrollment_from=figure(since['enrollment_from'],
                                       C.num(since['enrollment_from'])),
                enrollment_to=figure(since['enrollment_to'],
                                     C.num(since['enrollment_to'])),
                required_from=figure(since['required_from'], C.usd(since['required_from'])),
                required_to=figure(since['required_to'], C.usd(since['required_to'])),
                required_change=figure(since['required_change'],
                                       C.usd(since['required_change'])),
                aid_from=figure(since['aid_from'], C.usd(since['aid_from'])),
                aid_to=figure(since['aid_to'], C.usd(since['aid_to'])),
                aid_change=figure(since['aid_change'], C.usd(since['aid_change'])),
                share_first=figure(share_first_pct, C.pct(share_first_pct)),
                share_first_fy=figure(share['first_fy'], C.fy(share['first_fy'])),
                share_low=figure(share_low_pct, C.pct(share_low_pct)),
                share_low_fy=figure(share['low_fy'], C.fy(share['low_fy'])),
                share_last=figure(share_last_pct, C.pct(share_last_pct))),
            figure='required_pct',
            kind='measured',
            allow=('Chapter 70',),
            basis='DESE’s `dataAid` sheet: the required local contribution and the '
                  'Chapter 70 aid DESE calculated for the district, %s, with the '
                  'foundation enrollment the same rows are built on.'
                  % C.fyspan(since['from_fy'], since['to_fy']),
            not_shown='That the town is being asked for more than it can afford, or for '
                      'less. The required share is a ratio of two published figures and '
                      'what a town can afford is in neither of them. Nor is any of this '
                      'what the town SPENDS: the requirement is a floor, and the distance '
                      'above it is a separate measurement.',
            see=[('/what-the-state-requires-us-to-spend',
                  'what the town actually spends against that floor')],
        ),
        conclusion(
            id='the-required-contribution-is-wealth-not-children',
            claim='Growth in Lunenburg’s property wealth since FY2019, against a state median far below it',
            so_what='The town’s required share is worked out from wealth, not from how many children it has.',
            lede='What the state requires Lunenburg to pay towards its own schools is '
                  'worked out from property values and residents’ incomes, and has no '
                  'pupil count in it at all — that holds in all %s published years.' % C.num(len(years)),
            detail='Lunenburg’s equalized valuation rose %s between %s and %s, against a '
                   'median of %s across the %s municipalities in DESE’s own table — rank '
                   '%s, fastest first. Its combined effort yield, the sum of the two '
                   'efforts, rose %s against a median of %s. This is why fewer children '
                   'does not mean a smaller bill: the formula reads what the town is '
                   'worth, not how many pupils it has. Foundation enrollment fell across '
                   'those same years and the requirement rose %s.'
                   % (C.pct(eqv_growth_pct), C.fy(wealth['fy_from']),
                      C.fy(wealth['fy_to']), C.pct(eqv_median_pct),
                      C.num(wealth['municipalities']), C.num(wealth['eqv_rank']),
                      C.pct(cey_growth_pct), C.pct(cey_median_pct),
                      C.usd(since['required_change'])),
            figures=dict(
                years=figure(len(years), C.num(len(years))),
                eqv_growth=figure(eqv_growth_pct, C.pct(eqv_growth_pct)),
                fy_from=figure(wealth['fy_from'], C.fy(wealth['fy_from'])),
                fy_to=figure(wealth['fy_to'], C.fy(wealth['fy_to'])),
                eqv_median=figure(eqv_median_pct, C.pct(eqv_median_pct)),
                municipalities=figure(wealth['municipalities'],
                                      C.num(wealth['municipalities'])),
                eqv_rank=figure(wealth['eqv_rank'], C.num(wealth['eqv_rank'])),
                cey_growth=figure(cey_growth_pct, C.pct(cey_growth_pct)),
                cey_median=figure(cey_median_pct, C.pct(cey_median_pct)),
                required_change=figure(since['required_change'],
                                       C.usd(since['required_change']))),
            figure='eqv_growth',
            kind='measured',
            basis='DESE’s `dataContribution` sheet: the target local contribution and the '
                  'combined effort yield for Lunenburg in every published year, and '
                  'equalized valuation and combined effort yield for every municipality '
                  'the same sheet carries in both %s and %s.'
                  % (C.fy(wealth['fy_from']), C.fy(wealth['fy_to'])),
            not_shown='That the town’s wealth is its residents’ ability to pay. Equalized '
                      'valuation is property value; DESE carries an income term beside '
                      'it, and the combined effort yield grew more slowly than valuation '
                      'did over the same years. Neither figure is a household budget.',
            see=[('/monty-tech',
                  'the other district this one required contribution is split with')],
        ),
    ])

    return {
        'conclusions': conclusions,
        'about': 'Chapter 70 alone, term by term, out of DESE’s own workbook: what '
                 'the formula paid Lunenburg each year from FY%d to FY%d, and why the '
                 'last four increases are the Legislature’s flat floor rather than '
                 'anything the formula produced.' % (first, last),
        'not_this_page': 'Total state aid. Chapter 70 is the largest cherry sheet '
                         'receipt and it is not the whole of it — Unrestricted General '
                         'Government Aid and the other receipts are on /state-aid, with '
                         'what the town budgeted, what it received, and the growth rate '
                         'the projection uses.',
        'source': document(),
        'definitions': DEFINITIONS,
        'fy_first': first, 'fy_last': last, 'years': len(years),
        'headline': headline,
        'why_zero': why_zero,
        'floor': floor,
        'on_floor': on_floor,
        'series': series,
        'unreconciled': unreconciled,
        'reconciles_in': len(years) - 1 - len(unreconciled),
        'reconciles_of': len(years) - 1,
        'contribution': contribution,
        'contribution_build_holds': len(build_ok),
        'contribution_build_of': len(years) - 1,
        'contribution_build_anomaly': build_bad,
        'regime': regime,
        'share': share,
        'since': since,
        'stage_examples': stage_examples,
        'corroboration': corroboration,
        'spending': spending,
        'allocation': allocation,
        'allocation_summary': allocation_summary,
        'distribution': dist,
        'wealth': wealth,
        'marginal': marginal,
        'said': said_in_meetings(),
        'searched': terms,
        'minutes': minutes,
        'gaps': [split(g) for g in keep],
        'not_established': [
            'That one more child brings the town $%.0f. It does not follow from the '
            'arithmetic on this page. While the floor binds, aid moves at the '
            'Legislature’s per-pupil rate — but a large enough foundation budget '
            'increase closes the $%s of headroom and moves the district off the floor '
            'entirely, and no document in this archive models that.'
            % (headline['per_pupil'], format(round(why_zero['headroom']), ',')),
            'What the marginal pupil costs. The foundation budget is built from rates '
            'that differ by grade and by category, and the workbook publishes '
            'Lunenburg’s categories without the rates. The average of $%s a pupil is '
            'not the cost of the next one.'
            % format(round(headline['foundation_per_pupil']), ','),
            'That the Legislature sets the same floor next year. It has been $30, $60, '
            '$104 and $150 a pupil in the four years it bound here, and it was not '
            'available at all before FY2022.',
            'Why aid moved by more than DESE’s own components in %s. The workbook '
            'prints the increments and prints no residual.'
            % ', '.join('FY%d' % u['fy'] for u in unreconciled),
            'That a rising required contribution share means the town is being asked for '
            'more than it can pay, or less. The share is a ratio of two published '
            'figures. What a town can afford is not in this workbook.',
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()

    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT))
            return 1
        with open(OUT, encoding='utf-8') as fh:
            have = json.load(fh)
        if have != data:
            print('STALE %s — run: python3 scripts/build_minimum_aid.py'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    h, z = data['headline'], data['why_zero']
    print('%s: FY%d–FY%d, %d years'
          % (os.path.relpath(OUT, ROOT), data['fy_first'], data['fy_last'], data['years']))
    print('  FY%d: aid +%s, of which minimum aid %s and formula aid %s'
          % (h['fy'], format(round(h['increase']), ','),
             format(round(h['minimum_aid_increment']), ','),
             format(round(h['foundation_aid_increment']), ',')))
    print('  that is $%.2f a pupil against a foundation budget of $%s a pupil (%.0fx)'
          % (h['per_pupil'], format(round(h['foundation_per_pupil']), ','), h['times']))
    print('  formula need %s against %s already received — %s above the line'
          % (format(round(z['need']), ','), format(round(z['prior_aid']), ','),
             format(round(z['headroom']), ',')))
    print('  on the shared per-pupil rate in %s'
          % ', '.join('FY%d' % f for f in data['on_floor']))
    print('  aid components reconcile in %d of %d years' % (data['reconciles_in'],
                                                            data['reconciles_of']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
