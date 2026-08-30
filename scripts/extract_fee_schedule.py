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

What the fees are: per student, per sport, per season. A student playing three sports pays
three times. High school and middle school schedules are separate and do not combine toward
the sibling discount — the FAQ says so explicitly.

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

WORKBOOK = os.path.join(ROOT, 'sources', 'records-request-2026-06',
                        'athletics-by-sport-fy24-fy26.xlsx')
FAQ = os.path.join(ROOT, 'sources', 'txt', 'lhs-athletics-faq.txt')
MINUTES = os.path.join(ROOT, 'sources', 'minutes', 'text', 'school-committee',
                       '2025-02-26-minutes-7076.txt')

SOURCES = {
    'faq': dict(
        title='LHS Athletics FAQ (rschoolteams.com)',
        path='txt/lhs-athletics-faq.txt',
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
        path='records-request-2026-06/athletics-by-sport-fy24-fy26.xlsx',
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

# fy, level, item, amount, source id, and how to verify it. `check` is a workbook cell, a
# substring that must appear in a text source, or None where nothing can verify it.
SCHEDULE = [
    # ---- FY24 and FY25: the same schedule, two years -----------------------------------
    *[(fy, 'HS', 'full_pay',        250.00, 'workbook', cell) for fy, cell in ((2024, 'Spring!E3'), (2025, 'Spring!F3'))],
    *[(fy, 'HS', 'second_child',    140.00, 'workbook', cell) for fy, cell in ((2024, 'Spring!H3'), (2025, 'Spring!I3'))],
    *[(fy, 'HS', 'third_child',      85.00, 'workbook', cell) for fy, cell in ((2024, 'Spring!K3'), (2025, 'Spring!L3'))],
    *[(fy, 'HS', 'reduced_fee',      32.50, 'workbook', cell) for fy, cell in ((2024, 'Spring!Q3'), (2025, 'Spring!R3'))],
    *[(fy, 'MS', 'reduced_fee',      26.00, 'workbook', cell) for fy, cell in ((2024, 'Spring!T3'), (2025, 'Spring!U3'))],
    *[(fy, 'HS', 'family_cap',      475.00, 'faq', 'Total Cap per season=$475.00') for fy in (2024, 2025)],
    *[(fy, 'MS', 'full_pay',        200.00, 'faq', '1st student=$200.00') for fy in (2024, 2025)],
    *[(fy, 'MS', 'second_child',    150.00, 'faq', '2nd student=$150.00') for fy in (2024, 2025)],
    *[(fy, 'ANY', 'unified_track',  100.00, 'faq', 'Unified Track =$100.00') for fy in (2024, 2025)],

    # ---- FY26: voted 26 February 2025, and corroborated cell by cell -------------------
    (2026, 'HS', 'full_pay',          325.00, 'sc-2025-02-26', 'up \nto $325'),
    (2026, 'HS', 'full_pay_confirm',  325.00, 'workbook', 'Spring!G3'),
    (2026, 'MS', 'full_pay',          275.00, 'sc-2025-02-26', '$275 for Middle School'),
    (2026, 'HS', 'sibling_discount_pct', 25.0, 'sc-2025-02-26', 'A 25% discount for siblings'),
    (2026, 'HS', 'reduced_fee',        50.00, 'sc-2025-02-26', 'Reduced fee for high school to $50'),
    (2026, 'HS', 'reduced_fee_confirm', 50.00, 'workbook', 'Spring!S3'),
    (2026, 'MS', 'reduced_fee',        40.00, 'sc-2025-02-26', '$40 for middle school'),
    (2026, 'MS', 'reduced_fee_confirm', 40.00, 'workbook', 'Spring!V3'),
    (2026, 'ANY', 'family_cap',      1500.00, 'sc-2025-02-26', 'family cap of $1500'),

    # ---- FY27: reported, not published ------------------------------------------------
    (2027, 'HS', 'full_pay',      400.00, 'supt-email', None),
    (2027, 'HS', 'second_child',  300.00, 'supt-email', None),
    (2027, 'HS', 'third_child',   225.00, 'supt-email', None),
    (2027, 'ANY', 'family_cap',  1500.00, 'supt-email', None),
]

SCHOOL_YEAR = {2024: '2023-24', 2025: '2024-25', 2026: '2025-26', 2027: '2026-27'}


def main():
    import openpyxl
    wb = openpyxl.load_workbook(WORKBOOK, data_only=True)
    texts = {'faq': open(FAQ, encoding='utf-8', errors='ignore').read(),
             'sc-2025-02-26': open(MINUTES, encoding='utf-8', errors='ignore').read()}

    rows, failures, verified = [], [], 0
    for fy, level, item, amount, src, check in SCHEDULE:
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

        rows.append(dict(
            fy=fy, school_year=SCHOOL_YEAR[fy], level=level, item=item,
            amount=f'{amount:.2f}', unit='per student per sport per season',
            set_on=SOURCES[src]['set_on'], source=SOURCES[src]['title'],
            source_file=SOURCES[src]['path'], source_ref=check or '', verified=status))

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
    print('\nThe FAQ states no year anywhere. FY24 and FY25 are dated from the workbook’s '
          'own\nrate strip; FY26 from the School Committee vote that set it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
