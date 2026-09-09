"""Every rate this project knows about, with the year it applies to and who set it.

The reason this exists is one bug. `model/athletics.py` priced FY26 at $250 a season when
the district charged $325 — not a wrong number, a right number from the wrong year, taken
from a fee schedule that states its rates and never states which year they cover. It cost
31% of modelled fee revenue and forced a 1.452x calibration constant into the model to
absorb it, and nothing caught it because a rate with no date attached looks exactly like a
rate with the right date attached.

So: a register. Every rate carries **the fiscal year it applies to, the document that sets
it, and the date it was set.** Anything that cannot supply those three is recorded as a gap
rather than quietly used.

It deliberately includes rates the model does NOT use. A fee the town charges and does not
publish a schedule for is a finding, not an omission — and knowing the rate exists is what
makes it askable. `status` says which is which:

    verified        checked against a spreadsheet cell or a direct quotation
    recorded        from a document we hold, not machine-checkable
    reported        we have the figure, but the source is not public and we do not hold it
    not_published   the rate demonstrably exists and we have NO figure for it
    not_adopted     proposed and not voted, so there is no rate to have

The line between `reported` and `not_published` is the one that matters. "We know it is
$400 but cannot show you where that came from" and "we know a fee exists and have no idea
what it is" are different problems with different fixes, and collapsing them would hide
which question to ask.

`in_model` is separate from all of that, because "we hold this rate" and "the projection
uses it" are different claims and the project has confused them before. A contract rate can
be real, published, signed, and still deliberately not used — the paras' 2.0% is exactly
that, because the line has never behaved like the agreement.

    python3 scripts/build_rate_register.py

Reads sources/data/athletic-fee-schedule.csv and sources/contracts/CONTRACTS.md.
Writes sources/data/rate-register.csv
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEES = os.path.join(ROOT, 'sources', 'data', 'athletic-fee-schedule.csv')
CONTRACTS = os.path.join(ROOT, 'sources', 'contracts', 'CONTRACTS.md')
OUT = os.path.join(ROOT, 'sources', 'data', 'rate-register.csv')

FIELDS = ['fy', 'category', 'unit', 'item', 'value', 'value_type', 'set_on', 'expires',
          'source', 'source_file', 'source_ref', 'status', 'in_model']

# School Committee decisions that set a rate, or failed to. Quoted so the register can be
# checked against the minutes rather than believed.
SC = 'minutes/text/school-committee'
EMAIL26 = 'correspondence/2025-05-bus-fees-superintendent.txt'
EMAIL27 = 'correspondence/2026-08-17-bus-routes-and-fees-superintendent.txt'

# Bus fees, quoted from the Superintendent's own emails. These are for getting to SCHOOL --
# not to athletic events, which the revolving fund pays for. The distinction matters because
# a bus fee nets down GENERAL EDUCATION transportation, and the district's own budget
# workbook asks in its margin whether that line reflects "a reduction of $50K to accound for
# the money planned to come from the busing fees". That is rule 11 in the district's own
# handwriting: the line falls, and the cost has not.
BUS = [
    # FY26 -- May 2025 email, four tiers plus a waiver
    (2026, 'one student',                 180, EMAIL26, '$180 Families with 1 student'),
    (2026, 'one student, reduced',         50, EMAIL26, '$50 Families with 1 student that qualify for a reduced fee'),
    (2026, 'two or more students',        270, EMAIL26, '$270 Families with 2 or more students'),
    (2026, 'two or more, reduced',         75, EMAIL26, '$75 Families with 2 or more students that qualify for a reduced fee'),
    (2026, 'qualifying families',           0, EMAIL26, 'Free - Families that have submitted a Free/Reduced Application and qualify'),
    # FY27 -- August 2026 email. The single-student reduced tier is NOT restated.
    (2027, 'one student',                 180, EMAIL27, 'One child: $180.00'),
    (2027, 'two or more students',        270, EMAIL27, 'Family rate (2+ children): $270.00'),
    (2027, 'two or more, reduced',         75, EMAIL27, '$75 Families w/2+ children that qualify for a reduced fee'),
    (2027, 'qualifying families',           0, EMAIL27, 'Free-Families that have qualified'),
]

# Who is charged at all. Eligibility is part of the rate: a fee of $180 that applies to
# every 7-12 student is a different revenue line from one that applies to a fraction of K-6.
BUS_ELIGIBILITY = [
    (2026, 'grades K-6, under 2 miles', 'charged',   'Grades K-6 :  0-1.99 miles are charged'),
    (2026, 'grades K-6, 2 miles or more', 'no charge', 'Grades K-6 :  2 or more miles no charge'),
    (2026, 'grades 7-12', 'all charged',             'Grades 7-12 :  all students charged'),
]

# Every fee the district's payment portal sells, from its own navigation. The portal is
# itself client-side rendered and serves no amounts to a plain fetch, so this establishes
# that a fee EXISTS and nothing about what it costs. Recorded because a fee we cannot name
# is a fee we cannot ask about.
REVTRAK_CATALOGUE = ['Afterschool Activity Fee', 'Chromebook Repair Fee',
                     'Extended Day & ELC', 'Field Trips', 'LHS Parking Permit',
                     'Primary Preschool Program']
# ---------------------------------------------------------------- THE HOUSEHOLD BILL
# Every charge a Lunenburg family can meet that is NOT athletics and NOT the bus, with the
# document that sets it. Each `quote` below is asserted verbatim against `source_file` on
# every run, so a row here is a claim about a document rather than about our memory of one.
#
# THIS IS THE DATA-ENTRY POINT. When an amount arrives -- a fee schedule from the district,
# a handbook, an answer to a records request -- fill in `value`, set `status` to the right
# one of the five defined at the top of this file, and point `source_file` at the document.
# Nothing else has to change: `build_what_families_pay.py` reads the register, so a row with
# `value=''` renders as a named charge with no price and the same row renders as a priced
# line the moment the value is filled in. Adding a charge nobody has named yet is the same
# operation -- append a dict here.
#
# RULE 11 RUNS UNDER ALL OF IT. These are payments a HOUSEHOLD makes. They are not what the
# thing costs, and a fee arriving does not reduce an appropriation one-for-one -- several of
# these budget lines are already net of the fee.
HOUSEHOLD = [
    # THE STUDENT ACTIVITY FEE, VOTED. The February 2025 proposal was a base fee plus
    # per-activity fees and it is NOT what passed: on 7 May 2025 the committee took a single
    # universal rate instead. The amount is established by a motion that carried. The PERIOD
    # and the BASE are not -- the minute says "$70" and does not say per what, so this row
    # records the amount and `value_type` says the unit is not stated. Quoting the February
    # proposal as the charged rate would be rule 13 exactly.
    dict(fy=2026, category='activity_fee', unit='Student Activities',
         item='student activity fee', value='70.00', value_type='dollars — period not stated',
         set_on='2025-05-07',
         source='School Committee minutes, 7 May 2025 — moved, seconded, all approve',
         source_file=f'{SC}/2025-05-07-minutes-7207.txt',
         quote='a universal increase from $55 to $70 Mr. Sculimbrene makes a motion to '
               'approve the increase to $70, Mr. Beardmore seconds the motion, all approve',
         source_ref='universal increase from $55 to $70',
         status='verified'),
    # The rate it replaced, so the change is readable as a change rather than as a level.
    dict(fy=2025, category='activity_fee', unit='Student Activities',
         item='student activity fee', value='55.00', value_type='dollars — period not stated',
         set_on='2025-05-07',
         source='School Committee minutes, 7 May 2025 — the rate the $70 replaced',
         source_file=f'{SC}/2025-05-07-minutes-7207.txt',
         quote='a universal increase from $55 to $70',
         source_ref='from $55', status='recorded'),
    # FY2027: nothing in this archive restates it. That is NOT the same as the fee having
    # stopped -- it is charged, and the last rate anybody voted in public is the $70 above.
    dict(fy=2027, category='activity_fee', unit='Student Activities',
         item='student activity fee', value='', value_type='dollars',
         set_on='',
         source='Charged. No 2026-27 rate is restated anywhere in this archive; the last '
                'rate set in public is the $70 voted 7 May 2025',
         source_file='', quote=None, source_ref='', status='not_published'),

    # SCHOOL MEALS. Massachusetts funds universal free school meals, and the district's own
    # minutes record it choosing between the two programmes that deliver them. What that
    # establishes is that the standard reimbursable meal is not billed to a family. It does
    # NOT establish that a family spends nothing in the cafeteria -- a la carte items,
    # snacks and second meals are outside both programmes and no price list for them is
    # held here, which is a separate row below.
    dict(fy=2026, category='meals', unit='School meals',
         item='standard school meal', value='0.00', value_type='dollars per meal',
         set_on='2024-06-26',
         source='School Committee minutes, 26 June 2024 — CEP approved at Turkey Hill, '
                'against the Universal Meals Program elsewhere',
         source_file=f'{SC}/2024-06-26-minutes-6632.txt',
         quote='Our students would not see any difference',
         source_ref='CEP vs Universal Meal Program', status='recorded'),
    dict(fy=2027, category='meals', unit='School meals',
         item='standard school meal', value='0.00', value_type='dollars per meal',
         set_on='2025-04-16',
         source='School Committee minutes, 16 April 2025 — the state budget sustaining '
                'universal free school meals',
         source_file=f'{SC}/2025-04-16-minutes-7171.txt',
         quote='sustain funding for universal free school meals',
         source_ref='universal free school meals', status='recorded'),
    dict(fy='', category='meals', unit='School meals',
         item='a la carte and second meals', value='', value_type='dollars',
         set_on='',
         source='Outside the universal meal programmes. No price list is held here',
         source_file='', quote=None, source_ref='', status='not_published'),

    # THE PARKING PERMIT. A resident states the amount, in public comment, in a meeting the
    # town minuted. That is a figure from a document we hold -- and it is a RESIDENT saying
    # what they paid, not a schedule the district published, so it is `reported` rather than
    # `verified` and the page says which. The portal sells "LHS Parking Permit" and prints
    # no amount, which is the row this one stands beside rather than replaces.
    dict(fy=2025, category='other_fee', unit='Lunenburg High School',
         item='parking permit, as stated by a resident in public comment', value='50.00',
         value_type='dollars — period not stated', set_on='2025-03-12',
         source='School Committee minutes, 12 March 2025 — public comment, not a schedule',
         source_file=f'{SC}/2025-03-12-minutes-7098.txt',
         quote='I mean the $50 parking fee',
         source_ref='the $50 parking fee', status='reported'),

    # MUSIC. Established as a real household cost by a resident in the room where the
    # athletic fees were voted, and established as nothing else: the sum named is a
    # consumable bought from a shop, not a fee the district charges. There is no district
    # music fee in this archive, and no instrument rental rate.
    dict(fy='', category='other_fee', unit='Music', item='instruments, reeds and supplies',
         value='', value_type='dollars', set_on='2025-02-26',
         source='School Committee minutes, 26 February 2025 — public comment. Named as a '
                'real cost to families and paid to shops rather than to the district',
         source_file=f'{SC}/2025-02-26-minutes-7076.txt',
         quote='Instruments cost a lot, you need reeds and that can cost $50 a semester.',
         source_ref='reeds and that can cost $50 a semester', status='not_published'),

    # THE PROCESSING FEE. The Superintendent's own email says it exists and does not say
    # what it is. A family paying online pays it on top of every fee above.
    dict(fy=2027, category='other_fee', unit='RevTrak payment portal',
         item='online payment processing fee', value='', value_type='dollars',
         set_on='2026-08-17',
         source="Superintendent's email, 17 August 2026",
         source_file=EMAIL27,
         quote='RevTrak charges a small processing fee',
         source_ref='RevTrak charges a small processing fee', status='not_published'),
]


def household_rows():
    """The non-athletic household charges, each checked against the document it cites."""
    out = []
    for spec in HOUSEHOLD:
        r = dict(spec)
        quote = r.pop('quote')
        if quote is not None:
            # `source_file` is the PUBLISHED address (/docs/minutes/...), which is not
            # where the bytes are: the meetings mirror lives under sources/meetings/.
            rel = r['source_file']
            if rel.startswith('minutes/'):
                rel = 'meetings/' + rel[len('minutes/'):]
            path = os.path.join(ROOT, 'sources', rel)
            if not os.path.exists(path):
                sys.exit(f'household charge cites a document not on disk: {r["source_file"]}')
            hay = re.sub(r'\s+', ' ',
                         open(path, encoding='utf-8', errors='replace').read())
            hay = hay.replace('\u2019', "'").replace('\u2018', "'")
            if re.sub(r'\s+', ' ', quote).replace('\u2019', "'") not in hay:
                sys.exit(f'household charge quote not found in {r["source_file"]}: {quote!r}')
        r.setdefault('expires', '')
        r.setdefault('in_model', 'no')
        out.append(r)
    if len([r for r in out if r['status'] == 'not_published']) < 3:
        sys.exit('household charges: fewer than three carry no published amount, which is '
                 'the whole basis on which /what-families-pay calls its total a floor')
    return out


DECISIONS = [
    dict(fy=2026, category='bus_fee', unit='Transportation, to school',
         item='policy adopted', value='', value_type='note', set_on='2025-05-21', expires='',
         source='School Committee minutes, 21 May 2025 — Bus Fee Policy 3601.01 approved',
         source_file=f'{SC}/2025-05-21-minutes-7235.txt',
         source_ref='to approve the Bus Fee Policy 3601.01 as written',
         status='verified', in_model='no'),
    dict(fy=2026, category='facilities_fee', unit='Facilities', item='increase on prior schedule',
         value='50', value_type='percent', set_on='2025-02-26', expires='',
         source='School Committee minutes, 26 February 2025 — moved, seconded, approved',
         source_file=f'{SC}/2025-02-26-minutes-7076.txt',
         source_ref='Facilities Proposal to increase fees by 50%',
         status='not_published', in_model='no'),
    dict(fy=2026, category='activity_fee', unit='Student Activities', item='fee increase',
         value='', value_type='dollars', set_on='2025-02-26', expires='',
         source='School Committee minutes, 26 February 2025 — discussed, not voted',
         source_file=f'{SC}/2025-02-26-minutes-7076.txt',
         source_ref='Committee recommends Dr. Gilson',
         status='not_adopted', in_model='no'),
]

# Which contract rates the projection actually uses. Kept here rather than inferred,
# because "shown" and "used" have been conflated in this repo before.
IN_MODEL = {
    ('Teachers', 2027): 'shown, not used — the projection uses a measured trend',
    ('Paraprofessionals', 2027): 'deliberately not used — the line has never matched the agreement',
    ('Paraprofessionals', 2028): 'deliberately not used',
}


def bus_rows():
    text = open(os.path.join(ROOT, 'sources', EMAIL26.split('/')[0],
                             EMAIL26.split('/')[1]), encoding='utf-8').read()
    text27 = open(os.path.join(ROOT, 'sources', EMAIL27.split('/')[0],
                               EMAIL27.split('/')[1]), encoding='utf-8').read()
    bodies = {EMAIL26: text, EMAIL27: text27}
    out = []
    for fy, item, amount, src, quote in BUS:
        hay = re.sub(r'\s+', ' ', bodies[src])
        if re.sub(r'\s+', ' ', quote) not in hay:
            sys.exit(f'bus fee quote not found in {src}: {quote!r}')
        out.append(dict(
            fy=fy, category='bus_fee', unit='Transportation, to school', item=item,
            value=f'{amount:.2f}', value_type='dollars per family per year',
            set_on='2025-05' if src == EMAIL26 else '2026-08-17', expires='',
            source=("Superintendent's email, May 2025" if src == EMAIL26
                    else "Superintendent's email, 17 August 2026"),
            source_file=src, source_ref=quote, status='verified', in_model='no'))
    for fy, who, treatment, quote in BUS_ELIGIBILITY:
        out.append(dict(
            fy=fy, category='bus_fee', unit='Transportation, to school',
            item=f'eligibility — {who}', value='', value_type=treatment,
            set_on='2025-05', expires='',
            source="Superintendent's email, May 2025", source_file=EMAIL26,
            source_ref=quote, status='verified', in_model='no'))
    out.append(dict(
        fy=2027, category='bus_fee', unit='Transportation, to school',
        item='one student, reduced', value='', value_type='dollars per family per year',
        set_on='', expires='',
        source='Not restated in the 17 August 2026 email, which gives three tiers',
        source_file=EMAIL27, source_ref='',
        status='not_published', in_model='no'))
    for name in REVTRAK_CATALOGUE:
        out.append(dict(
            fy='', category='other_fee', unit='Lunenburg Public Schools', item=name,
            value='', value_type='dollars', set_on='', expires='',
            source='RevTrak payment portal navigation (lunenburg.revtrak.net) — the portal '
                   'renders in JavaScript and serves no amounts to a plain fetch',
            source_file='', source_ref='https://lunenburg.revtrak.net/r2#/v/bus-fees',
            status='not_published', in_model='no'))
    return out


def contract_rows():
    """Parse the unit table in CONTRACTS.md rather than retyping it."""
    md = open(CONTRACTS, encoding='utf-8').read()
    block = re.search(r'\| Unit \| Term \| Raises by year \| Expires \|\n\|[-| ]+\|\n((?:\|.*\n)+)', md)
    if not block:
        sys.exit('CONTRACTS.md: could not find the "Every school unit" table')

    rows, units = [], 0
    for line in block.group(1).strip().split('\n'):
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 4:
            continue
        unit_raw, term, raises, expires = cells[:4]
        unit = re.sub(r'\*\*|\(.*?\)', '', unit_raw).strip().rstrip(',')
        units += 1

        exp = expires.replace('**', '').strip()
        first = re.search(r'FY(\d{2})', term)
        pcts = re.findall(r'([\d.]+)%', raises)

        if not pcts:
            # Recorded because knowing the contract exists is what makes it askable.
            rows.append(dict(
                fy='', category='contract_cola', unit=unit, item='cost-of-living adjustment',
                value='', value_type='percent', set_on='', expires=exp,
                source=f'Lunenburg school employee contracts — term {term}',
                source_file='contracts/CONTRACTS.md', source_ref=raises,
                status='not_published' if 'not public' in raises else 'recorded',
                in_model='no'))
            continue

        start = 2000 + int(first.group(1)) if first else None
        for i, p in enumerate(pcts):
            fy = start + i if start else ''
            rows.append(dict(
                fy=fy, category='contract_cola', unit=unit,
                item='cost-of-living adjustment to the salary scale',
                value=f'{float(p):.1f}', value_type='percent', set_on='', expires=exp,
                source=f'Lunenburg school employee contracts — {unit}, term {term}',
                source_file='contracts/CONTRACTS.md',
                source_ref=f'{unit} | {term} | {raises}',
                status='recorded',
                in_model=IN_MODEL.get((unit, fy), 'no')))
    if units < 4:
        sys.exit(f'CONTRACTS.md: parsed only {units} units; the table has changed shape')
    return rows


def fee_rows():
    if not os.path.exists(FEES):
        sys.exit(f'missing {FEES} — run scripts/extract_fee_schedule.py first')
    out = []
    for r in csv.DictReader(open(FEES)):
        if r['item'].endswith('_confirm'):
            continue          # corroborating duplicates, already counted
        out.append(dict(
            fy=r['fy'], category='athletic_fee', unit=r['level'], item=r['item'],
            value=r['amount'], value_type='percent' if r['item'].endswith('_pct') else 'dollars',
            set_on=r['set_on'], expires='',
            source=r['source'], source_file=r['source_file'], source_ref=r['source_ref'],
            status=('verified' if r['verified'] not in ('not verifiable', 'source not held')
                    else 'reported' if r['verified'] == 'source not held'
                    else 'recorded'),
            in_model='yes' if r['fy'] in ('2026', '2027') else 'reference'))
    return out


def main():
    rows = fee_rows() + bus_rows() + contract_rows() + household_rows() + DECISIONS
    rows.sort(key=lambda r: (r['category'], str(r['fy']), r['unit'], r['item']))

    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f'wrote {os.path.relpath(OUT, ROOT)}  ({len(rows)} rates)\n')
    by_cat, by_status = {}, {}
    for r in rows:
        by_cat[r['category']] = by_cat.get(r['category'], 0) + 1
        by_status[r['status']] = by_status.get(r['status'], 0) + 1
    for k, v in sorted(by_cat.items()):
        print(f'  {k:<16} {v:>3}')
    print()
    for k, v in sorted(by_status.items()):
        print(f'  {k:<16} {v:>3}')

    print('\nRates we know exist and cannot state:')
    for r in rows:
        if r['status'] in ('not_published', 'not_adopted'):
            print(f"  {r['category']:<16} {r['unit']:<22} {r['item']:<34} {r['status']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
