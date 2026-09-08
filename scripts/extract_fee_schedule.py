"""The athletic fee schedule, one row per fee, per level, per fiscal year — with its source.

Why this file exists. `model/athletics.py` priced FY26 at $250 for a high school season.
The district charged $325. The model was not using a wrong number; it was using a **right
number from the wrong year**, taken from the LHS athletics FAQ — which states its rates and
never states which year they apply to. An undated schedule gets applied to whatever year
you happen to be modelling, and nothing complains.

That single error was worth 31% of modelled fee revenue, and it forced a 1.452x calibration
constant and a two-sided range into the model to absorb it.

So every rate here carries three things it previously lacked: **the fiscal year it applies
to, the document that sets it, and the date it was set.** A rate with no year attached does
not go in this table.

**And what the fees are is NOT one sentence, which is the second reason this file exists.**
This docstring used to say "per student, per sport, per season" flatly, and the `unit`
column stamped that identical string onto all 31 rows — the family cap included, where
"per student per sport" means nothing at all. Nothing had been read off any source to
justify it. So the period is now carried per row, with the words that establish it, and it
comes out three different ways: STATED for the FAQ's own "Per Season Breakdown" and its
"Total Cap per season"; STRUCTURAL for the workbook, which never writes the word season but
keeps its rate strip on three worksheets named for the three seasons; and NOT ESTABLISHED
for the FY26 and FY27 family caps and for anything sourced to the email we do not hold.

The per-SPORT half is ours as well. No document here states these fees as a charge per
sport. At the high school it follows from a rule the FAQ does state — "Only one sport per
season is allowed" — so per sport and per season coincide there. The FAQ states no such
rule for middle school. High school and middle school schedules are separate and do not
combine toward the sibling discount; the FAQ does say that explicitly.

**Curated, then checked.** The rows below are editorial: knowing that a School Committee
vote in February 2025 sets the following school year is a judgement, not something a script
can read off. But every figure that CAN be checked against its source is, at the cell or the
line, and this refuses to write if any of them has moved. That is the same split as
`build_source_index.py`: the descriptions are ours, everything checkable is checked.

    python3 scripts/extract_fee_schedule.py

Writes sources/data/athletic-fee-schedule.csv
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'athletic-fee-schedule.csv')

WORKBOOK = os.path.join(ROOT, 'sources', 'town-ledgers', 'account-details',
                        'athletics-by-sport-fy2024-fy2026.xlsx')
FAQ = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                   'lhs-athletics-faq.txt')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text', 'school-committee',
                       '2025-02-26-minutes-7076.txt')

SOURCES = {
    'faq': dict(
        title='LHS Athletics FAQ (rschoolteams.com)',
        path='district-budget/text/lhs-athletics-faq.txt',
        set_on='',
        note='States rates and no year anywhere in the document. It matches what was '
             'charged in FY24 and FY25 and was still the posted schedule long after the '
             'rates changed, so a family checking the website got the wrong number. This '
             'is the source the model was wrongly using for FY26.'),
    'sc-2025-02-26': dict(
        title='School Committee minutes, 26 February 2025 — "Increasing New & Existing Revenues"',
        path='minutes/text/school-committee/2025-02-26-minutes-7076.txt',
        set_on='2025-02-26',
        note='Voted and approved by roll call. A fee voted in February 2025 applies to the '
             '2025-26 school year, which is FY26. This is the only source that gives the '
             'FY26 middle school rate and the sibling structure.'),
    'workbook': dict(
        title='District athletics workbook, by sport (Town filename: Copy of Athletics 24.25 (1).xlsx)',
        path='town-ledgers/account-details/athletics-by-sport-fy2024-fy2026.xlsx',
        set_on='',
        note='Obtained by records request, 17 June 2026. Carries the rate strip for three '
             'school years side by side, which is what makes each rate datable.'),
    'supt-email': dict(
        title="Superintendent's email to families, August 2026",
        path='',
        set_on='2026-08',
        note='NOT HELD AND NOT PUBLISHED. We could not find the FY27 schedule posted '
             'anywhere. Recorded because it is the only account of the FY27 rates we have, '
             'and flagged so nobody treats it as a checkable source.'),
}

# ---------------------------------------------------------------------------------------
# WHAT PERIOD EACH RATE COVERS, and how we know.
#
# THIS COLUMN USED TO BE A CONSTANT. Every one of the 31 rows carried the identical string
# `per student per sport per season`, stamped on by this script rather than read off
# anything, INCLUDING the family cap -- where "per student per sport" is meaningless and
# the season half is the single most consequential unknown in the whole schedule. A cap of
# $1,500 read per season and read per year are different bills, and a constant in a `unit`
# column asserted one of them on every row without a source. That is rule 13's shape
# exactly: something derived, quoted as though it were observed.
#
# So the unit is now per row, with the words that establish it, and three states:
#
#   stated           the source names the period in its own words
#   structural       the source does not say it in words, but its own construction fixes
#                    it -- the workbook's rate strip is repeated on three worksheets, one
#                    per season, and applied to each worksheet's own athlete counts
#   not established  nothing in the source fixes it, and this schedule says so
#
# AND "PER SPORT" IS OURS, NOT THEIRS. No document in this archive states these fees as a
# charge per sport. The FAQ's heading is `Per Season Breakdown`. Per sport and per season
# coincide AT THE HIGH SCHOOL because the same FAQ says only one sport per season is
# allowed there -- an inference from a rule the document does state, which is why the unit
# below is written per SEASON and the per-sport equivalence is carried as a note. The FAQ
# states no such rule for middle school.
FAQ_SEASON_HEADING = 'Per Season Breakdown:'
FAQ_ONE_SPORT = 'Only one sport per season is allowed.'
SEASON_SHEETS = ('Fall', 'Winter', 'Spring')

UNITS = {
    'faq-season': dict(
        unit='per student, per season',
        status='stated',
        basis='The FAQ prints the heading "%s" immediately above these amounts, in both '
              'the high school and the middle school block.' % FAQ_SEASON_HEADING,
        quote=FAQ_SEASON_HEADING),
    'faq-cap-season': dict(
        unit='per family, per season',
        status='stated',
        basis='The FAQ names the period inside the label itself: "Total Cap per season".',
        quote='Total Cap per season'),
    'faq-unstated': dict(
        unit='not established',
        status='not established',
        basis='The FAQ lists this as a bullet BELOW both "%s" blocks and under no heading '
              'of its own. Nothing in the document says what period it covers.'
              % FAQ_SEASON_HEADING,
        quote=None),
    'workbook-season': dict(
        unit='per student, per season',
        status='structural',
        basis='The workbook nowhere writes the word season. Its own construction fixes it: '
              'the rate strip is row 3 of three worksheets named %s, the same rates appear '
              'on more than one of them, and each is applied to that worksheet\'s own '
              'athlete counts.' % ', '.join(SEASON_SHEETS),
        quote=None),
    'minutes-corroborated': dict(
        unit='per student, per season',
        status='structural',
        basis='The 26 February 2025 minutes state an amount and no period. The same amount '
              'sits in the workbook\'s per-season rate strip, in the 25/26 column, which is '
              'the corroborating row recorded separately below.',
        quote=None),
    'minutes-unstated': dict(
        unit='not established',
        status='not established',
        basis='The 26 February 2025 minutes state an amount and no period, and no cell of '
              'the district workbook carries this figure.',
        quote=None),
    'minutes-pct': dict(
        unit='percent of the fee, for an additional child',
        status='stated',
        basis='A percentage discount off another rate. It carries no period of its own.',
        quote='A 25% discount for siblings'),
    'cap-unstated': dict(
        unit='not established',
        status='not established',
        basis='THE ONE THAT MATTERS. The cap that preceded this one was stated per season, '
              'in those words. This one is stated with no period at all, and no cell of '
              'the district workbook carries a family cap of any amount. Read per season '
              'and read per year it is a different bill, and nothing published says which.',
        quote=None),
    'not-held': dict(
        unit='not established',
        status='not established',
        basis='The source is an email to families that this archive does not hold, so '
              'nothing about it can be quoted -- the amount included.',
        quote=None),
}

# fy, level, item, amount, source id, how to verify it, and which unit above applies.
# `check` is a workbook cell, a substring that must appear in a text source, or None where
# nothing can verify it.
SCHEDULE = [
    # ---- FY24 and FY25: the same schedule, two years -----------------------------------
    *[(fy, 'HS', 'full_pay',        250.00, 'workbook', cell, 'workbook-season') for fy, cell in ((2024, 'Spring!E3'), (2025, 'Spring!F3'))],
    *[(fy, 'HS', 'second_child',    140.00, 'workbook', cell, 'workbook-season') for fy, cell in ((2024, 'Spring!H3'), (2025, 'Spring!I3'))],
    *[(fy, 'HS', 'third_child',      85.00, 'workbook', cell, 'workbook-season') for fy, cell in ((2024, 'Spring!K3'), (2025, 'Spring!L3'))],
    *[(fy, 'HS', 'reduced_fee',      32.50, 'workbook', cell, 'workbook-season') for fy, cell in ((2024, 'Spring!Q3'), (2025, 'Spring!R3'))],
    *[(fy, 'MS', 'reduced_fee',      26.00, 'workbook', cell, 'workbook-season') for fy, cell in ((2024, 'Spring!T3'), (2025, 'Spring!U3'))],
    *[(fy, 'HS', 'family_cap',      475.00, 'faq', 'Total Cap per season=$475.00', 'faq-cap-season') for fy in (2024, 2025)],
    *[(fy, 'MS', 'full_pay',        200.00, 'faq', '1st student=$200.00', 'faq-season') for fy in (2024, 2025)],
    *[(fy, 'MS', 'second_child',    150.00, 'faq', '2nd student=$150.00', 'faq-season') for fy in (2024, 2025)],
    *[(fy, 'ANY', 'unified_track',  100.00, 'faq', 'Unified Track =$100.00', 'faq-unstated') for fy in (2024, 2025)],

    # ---- FY26: voted 26 February 2025, and corroborated cell by cell -------------------
    (2026, 'HS', 'full_pay',          325.00, 'sc-2025-02-26', 'up \nto $325', 'minutes-corroborated'),
    (2026, 'HS', 'full_pay_confirm',  325.00, 'workbook', 'Spring!G3', 'workbook-season'),
    (2026, 'MS', 'full_pay',          275.00, 'sc-2025-02-26', '$275 for Middle School', 'minutes-unstated'),
    (2026, 'HS', 'sibling_discount_pct', 25.0, 'sc-2025-02-26', 'A 25% discount for siblings', 'minutes-pct'),
    (2026, 'HS', 'reduced_fee',        50.00, 'sc-2025-02-26', 'Reduced fee for high school to $50', 'minutes-corroborated'),
    (2026, 'HS', 'reduced_fee_confirm', 50.00, 'workbook', 'Spring!S3', 'workbook-season'),
    (2026, 'MS', 'reduced_fee',        40.00, 'sc-2025-02-26', '$40 for middle school', 'minutes-corroborated'),
    (2026, 'MS', 'reduced_fee_confirm', 40.00, 'workbook', 'Spring!V3', 'workbook-season'),
    (2026, 'ANY', 'family_cap',      1500.00, 'sc-2025-02-26', 'family cap of $1500', 'cap-unstated'),

    # ---- FY27: reported, not published ------------------------------------------------
    (2027, 'HS', 'full_pay',      400.00, 'supt-email', None, 'not-held'),
    (2027, 'HS', 'second_child',  300.00, 'supt-email', None, 'not-held'),
    (2027, 'HS', 'third_child',   225.00, 'supt-email', None, 'not-held'),
    (2027, 'ANY', 'family_cap',  1500.00, 'supt-email', None, 'not-held'),
]

SCHOOL_YEAR = {2024: '2023-24', 2025: '2024-25', 2026: '2025-26', 2027: '2026-27'}


def workbook_season_checks(wb):
    """The workbook's own construction, asserted — because `structural` rests on it.

    Two claims are made about this workbook on the page and in the `unit` column, and
    neither is a figure, so nothing else here would catch them moving:

      1. the rate strip lives on worksheets named for the three seasons, and the SAME
         rate appears on more than one of them — which is what makes a rate per season
         rather than per year;
      2. no cell of row 3 on any of them carries a family cap. The cap is in the minutes
         and nowhere else, which is exactly why its period cannot be corroborated the way
         the per-student rates can.
    """
    missing = [n for n in SEASON_SHEETS if n not in wb.sheetnames]
    if missing:
        return [f'the workbook no longer has the season worksheet(s) '
                f'{", ".join(missing)} — the per-season unit on every workbook row rests '
                f'on the sheet names'], None
    strips = {}
    for name in SEASON_SHEETS:
        ws = wb[name]
        strips[name] = {ws.cell(3, col).coordinate[:-1]: ws.cell(3, col).value
                        for col in range(1, 40)
                        if isinstance(ws.cell(3, col).value, (int, float))}
    shared = [col for col in strips['Spring']
              if sum(1 for n in SEASON_SHEETS if col in strips[n]) > 1]
    problems = []
    if len(shared) < 2:
        problems.append('the workbook rate strip no longer repeats on more than one season '
                        'worksheet — the per-season unit is inferred from that repetition')
    for col in shared:
        vals = {n: strips[n][col] for n in SEASON_SHEETS if col in strips[n]}
        if len(set(vals.values())) != 1:
            problems.append(f'column {col} row 3 differs between season worksheets '
                            f'({vals}) — the seasons are not charged at one rate')
    caps = {row[3] for row in SCHEDULE if row[2] == 'family_cap'}
    for name in SEASON_SHEETS:
        for col, val in strips[name].items():
            if val in caps:
                problems.append(f'{name}!{col}3 = {val}, which is a family cap amount — '
                                'this schedule states that no cell of the workbook carries '
                                'a family cap, and that is now false')
    return problems, dict(sheets=list(SEASON_SHEETS),
                          shared_columns=sorted(shared),
                          strip_row=3)


def main():
    import openpyxl
    wb = openpyxl.load_workbook(WORKBOOK, data_only=True)
    texts = {'faq': open(FAQ, encoding='utf-8', errors='ignore').read(),
             'sc-2025-02-26': open(MINUTES, encoding='utf-8', errors='ignore').read()}

    rows, failures, verified = [], [], 0

    # The two sentences the FAQ-sourced units quote, and the rule the per-SPORT reading
    # rests on. A unit citing words that are no longer in the document is rule 13's whole
    # subject, so the words are asserted rather than trusted.
    faq_flat = re.sub(r'\s+', ' ', texts['faq'])
    if faq_flat.count(re.sub(r'\s+', ' ', FAQ_SEASON_HEADING)) < 2:
        failures.append(f'the FAQ no longer prints {FAQ_SEASON_HEADING!r} above both fee '
                        'blocks — the "stated" unit on those rows has nothing behind it')
    if re.sub(r'\s+', ' ', FAQ_ONE_SPORT) not in faq_flat:
        failures.append(f'the FAQ no longer states {FAQ_ONE_SPORT!r} — that rule is the '
                        'only thing making a high school season fee also a per-sport fee')

    wb_problems, wb_structure = workbook_season_checks(wb)
    failures.extend(wb_problems)

    for fy, level, item, amount, src, check, unit_key in SCHEDULE:
        status = 'not verifiable'
        if check and src == 'workbook':
            sheet, cell = check.split('!')
            got = wb[sheet][cell].value
            if got is None or abs(float(got) - amount) > 0.005:
                failures.append(f'{check} = {got!r}, expected {amount}')
            else:
                status, verified = f'{check}', verified + 1
        elif check and src in texts:
            # Minutes are wrapped by the extractor, so compare with whitespace collapsed.
            hay = re.sub(r'\s+', ' ', texts[src])
            needle = re.sub(r'\s+', ' ', check)
            if needle not in hay:
                failures.append(f'{src}: {needle!r} not found in the source text')
            else:
                status, verified = 'quoted in source', verified + 1
        elif src == 'supt-email':
            status = 'source not held'

        u = UNITS[unit_key]
        if u['quote'] and src in texts:
            if re.sub(r'\s+', ' ', u['quote']) not in re.sub(r'\s+', ' ', texts[src]):
                failures.append(f'the words establishing the unit on {fy} {level} {item} '
                                f'({u["quote"]!r}) are not in {SOURCES[src]["path"]}')

        rows.append(dict(
            fy=fy, school_year=SCHOOL_YEAR[fy], level=level, item=item,
            amount=f'{amount:.2f}', unit=u['unit'], unit_status=u['status'],
            unit_basis=u['basis'], unit_quote=u['quote'] or '',
            set_on=SOURCES[src]['set_on'], source=SOURCES[src]['title'],
            source_file=SOURCES[src]['path'], source_ref=check or '', verified=status))

    # The FY24/FY25 identity the schedule states about itself: the three published high
    # school rates sum to exactly the cap the FAQ prints beside them. It is the check that
    # tells you what a cap at that level was FOR, and it is the reason the FY27 cap looks
    # like a different animal — 400 + 300 + 225 does not come near 1,500.
    old = {(r['fy'], r['level'], r['item']): float(r['amount']) for r in rows}
    ladder = [old.get((2025, 'HS', k)) for k in ('full_pay', 'second_child', 'third_child')]
    cap25 = old.get((2025, 'HS', 'family_cap'))
    if None in ladder or cap25 is None:
        failures.append('the FY25 high school ladder or its cap is missing — the identity '
                        'this schedule checks itself against cannot be evaluated')
    elif abs(sum(ladder) - cap25) > 0.005:
        failures.append(f'FY25: the three published rates sum to {sum(ladder):.2f} against '
                        f'a printed cap of {cap25:.2f}. That identity is quoted downstream.')

    if failures:
        print('refusing to write — a rate no longer matches its source:')
        for f in failures:
            print(f'  {f}')
        return 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f'wrote {os.path.relpath(OUT, ROOT)}  ({len(rows)} rows, {verified} verified '
          f'against a cell or a quotation)\n')
    hdr = f"{'FY':<6}{'year':<10}{'HS full':>9}{'MS full':>9}{'HS red':>8}{'MS red':>8}{'cap':>9}  set on"
    print(hdr); print('-' * len(hdr))
    for fy in (2024, 2025, 2026, 2027):
        g = {(r['level'], r['item']): r['amount'] for r in rows if r['fy'] == fy}
        pick = lambda lvl, it: g.get((lvl, it), g.get(('ANY', it), '—'))
        seton = next((r['set_on'] for r in rows if r['fy'] == fy and r['set_on']), '—')
        print(f"{fy:<6}{SCHOOL_YEAR[fy]:<10}{pick('HS','full_pay'):>9}{pick('MS','full_pay'):>9}"
              f"{pick('HS','reduced_fee'):>8}{pick('MS','reduced_fee'):>8}"
              f"{pick('HS','family_cap'):>9}  {seton}")
    print('\nThe FAQ states no year anywhere. FY24 and FY25 are dated from the workbook\u2019s '
          'own\nrate strip; FY26 from the School Committee vote that set it.')
    print(f"\nUnit, which is no longer a constant: "
          + ', '.join(f'{n} {st}' for st, n in sorted(
              ((sum(1 for r in rows if r['unit_status'] == s), s)
               for s in {r['unit_status'] for r in rows}), reverse=True)))
    print(f"The workbook rate strip repeats across {', '.join(wb_structure['sheets'])} in "
          f"columns {', '.join(wb_structure['shared_columns'])}; no cell of it carries a "
          "family cap.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
