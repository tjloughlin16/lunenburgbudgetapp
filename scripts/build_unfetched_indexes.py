#!/usr/bin/env python3
"""The `index.csv` for every source tree NO FETCHER WRITES.

    python3 scripts/build_unfetched_indexes.py
    python3 scripts/build_unfetched_indexes.py --check   # fail if any of them is stale

WHY THIS EXISTS

TJ, 2 October 2026: *"i tried to find the landscaping contract, which i believe we have,
and i couldnt find it"*. We hold it --
`sources/town-ledgers/purchase-orders/po-closed-fy2025-parks-grounds-bid.pdf` -- and it
was in no search result, because `build_search_index.py` reads `sources/<folder>/index.csv`
and four trees had none: `contracts`, `town-ledgers`, `correspondence`, `peer-districts`.

The text was already extracted for most of them. The missing thing was the CATALOGUE, and
the indexer is right to demand one: *a stray text file with no label and no upstream must
not enter with no citation*. So this writes the catalogue rather than routing around the
gate.

`town-budget`, `town-supplementary`, `state-dese`, `district-budget` and
`town-annual-reports` get their `index.csv` from the fetcher that downloaded them
(`fetch_town_docs.py` and its siblings) -- the register a fetch keeps as it goes. Nothing
in these four trees came off a fetcher: they arrived by records request, by email, or were
mirrored by hand from another district's website. So the labels are editorial and live
here, while everything checkable is computed:

  * `bytes` and `sha256` are read off the file, never copied from anywhere
  * `upstream` is taken from `build_source_index.SOURCE_URLS` -- the one place in this
    repo where a hand-recorded address lives, and the one `verify_source_copies.py`
    re-checks by downloading the file and matching the sha256. It is not retyped here.
  * a row is written only where a document EXISTS and has extracted text, so the index
    cannot promise a file the tree does not hold

ON `upstream`, AND THE ONE THING THIS CONTRACT CANNOT CARRY

Rule 12: *"Obtained from the Town by records request" plus a date IS an address.* But
`fy28/src/pages/Search.tsx` renders `upstream` as `<a href=...>publisher's copy</a>`, so
prose in that column would publish a broken link. The column therefore holds a URL or
nothing, and for a document that did not come off a website the address is carried in the
LABEL, which is what a searcher actually reads:

    ... (records request, August 2025)

That is also the fix for the thing that went wrong. The label is the only part of a
document a searcher sees, so it carries the words the document uses about itself --
including, where it differs from ours, THE PUBLISHER'S OWN FILENAME (rule 12's second
requirement). The grounds bid is filed under the town's word, `grounds`; the town's own
filename for it is `Landscaping Costs.pdf`, and quoting that in the label is what makes it
reachable by the word TJ searched without renaming the thing.
"""
import argparse
import csv
import hashlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import build_source_index as B  # noqa: E402  -- SOURCE_URLS, the recorded addresses

HEADER = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read']

# The district's own copy of the teachers' agreement: 70pp on the HR page, against DESE's
# 72pp filing which is the same document plus the stipend appendix. Only the extracted
# text survives here -- the PDF was dropped rather than store 53MB twice -- so it has no
# `local` and SOURCE_URLS, which is keyed on files we hold, has no row for it. The address
# is recorded in sources/contracts/CONTRACTS.md and copied here, which is the only
# hand-typed URL in this file.
LEA_DISTRICT_COPY = 'https://drive.google.com/file/d/19IaKYDVtYXgJ63J0MOod-8Io6F3oZ6dw/view'

# (local, text, label). `local` '' means we hold no original, only the text.
# `text` == `local` means the document IS a text file -- an email, a markdown note -- and
# not an extraction from something else.
TREES = {
    'contracts': [
        ('pdf/dese-teacher-contract.pdf', 'txt/dese-teacher-contract.txt',
         "Teachers' agreement (Lunenburg Education Association), 1 July 2024 to 30 June 2027 "
         "— raises of 2.5%, 4.0% and 3.5%, as filed with DESE"),
        ('', 'txt/lea-teachers-2024-2027.txt',
         "Teachers' agreement (Lunenburg Education Association), 2024–2027 — the district's own "
         "70-page copy; extracted text only, the PDF was not kept"),
        ('pdf/paraprofessional-fy26-fy28.pdf', 'txt/paraprofessional-fy26-fy28.txt',
         "Paraprofessional agreement (AFSCME Council 93, Local 503), FY2026 to FY2028 — raises of "
         "3.0%, 2.0% and 2.0%"),
        ('pdf/paraprofessional-salary-fy26-fy28.pdf', 'txt/paraprofessional-salary-fy26-fy28.txt',
         "Paraprofessional salary schedule, FY2026 to FY2028 — hourly rates by classification "
         "(Para 1–4) and step"),
        ('pdf/custodial-2023-2026.pdf', 'txt/custodial-2023-2026.txt',
         "Custodians' agreement (AFSCME Council 93), 2023 to 2026 — the agreement that expired "
         "30 June 2026"),
        ('pdf/custodial-moa-2026.pdf', 'txt/custodial-moa-2026.txt',
         "Custodians' memorandum of agreement, 29 July 2026 — successor terms of 3.5%, 2.5% and "
         "2.5% through FY2029"),
        ('pdf/nonaffiliated-salary-schedule.pdf', 'txt/nonaffiliated-salary-schedule.txt',
         "Non-affiliated salary schedule — hourly rates for staff in no bargaining unit: "
         "extended-day aides, cafeteria monitors, greenhouse assistant, COTA"),
        ('pdf/nonaffiliated-benefits.pdf', 'txt/nonaffiliated-benefits.txt',
         "Non-affiliated employee benefits — the benefit terms for the same group"),
        ('pdf/dese-superintendent-contract.pdf', 'txt/dese-superintendent-contract.txt',
         "Superintendent's contract, 1 July 2018 to 30 June 2021 — DESE's filing, expired, and "
         "the most recent one published"),
        ('pdf/dese-administrator-contract.pdf', 'txt/dese-administrator-contract.txt',
         "Principal's contract, 1 July 2019 to 30 June 2022 — DESE's filing, a template, expired"),
        ('CONTRACTS.md', 'CONTRACTS.md',
         "Every school union contract side by side: term, raises by year, salary scales, and "
         "what is still not public (our research note)"),
    ],
    'peer-districts': [
        ('groton-dunstable-fy27-budget-book.pdf', 'groton-dunstable-fy27-budget-book.txt',
         "Groton-Dunstable Regional School District, FY2027 budget book — 132 pages, a third "
         "year of cuts and an override request"),
        ('ashburnham-westminster-fy27-presentation.pdf',
         'ashburnham-westminster-fy27-presentation.txt',
         "Ashburnham-Westminster Regional School District, FY2027 budget presentation — the "
         "district that protected athletics, arts and music and cut teaching posts instead"),
        ('ashburnham-westminster-fy27-detail.pdf', 'ashburnham-westminster-fy27-detail.txt',
         "Ashburnham-Westminster Regional School District, FY2027 budget line by line"),
        ('ayer-shirley-fy27-expenses.pdf', 'ayer-shirley-fy27-expenses.txt',
         "Ayer Shirley Regional School District, FY2027 proposed budget by function — health "
         "insurance up 14.4%"),
        ('north-middlesex-finance-subcommittee.pdf', 'north-middlesex-finance-subcommittee.txt',
         "North Middlesex Regional School District, finance subcommittee packet, 1 December 2025 "
         "— the FY2027 deficit at 3% against 5% growth"),
        ('wachusett-fy27-budget-presentation.pdf', 'wachusett-fy27-budget-presentation.txt',
         "Wachusett Regional School District, FY2027 budget presentation — member-town "
         "assessments and enrolment by town"),
    ],
    'town-ledgers': [
        # The period 12 package: emailed by the Town Manager, 2 September 2026.
        ('expenses/glytdbud-expense-fy2026-p12-gf-all.pdf',
         'expenses/glytdbud-expense-fy2026-p12-gf-all.txt',
         "Town general fund spending against budget, FY2026 through June (period 12), account by "
         "account — MUNIS year-to-date budget report, not the year-end close "
         "(emailed by the Town Manager, 2 September 2026)"),
        # The period 9 package: a records request answered by the Town before 14 August 2026.
        ('expenses/glytdbud-expense-fy2026-p09-gf-all.pdf',
         'expenses/glytdbud-expense-fy2026-p09-gf-all.txt',
         "Town general fund spending against budget, FY2026 through 31 March 2026, by department "
         "— MUNIS year-to-date budget report (records request, August 2026)"),
        ('revenue/glytdbud-revenue-fy2026-p09-gf-all.pdf',
         'revenue/glytdbud-revenue-fy2026-p09-gf-all.txt',
         "Town general fund revenue against budget, FY2026 through 31 March 2026 — MUNIS "
         "year-to-date budget report (records request, August 2026)"),
        ('expenses/glytdbud-expense-fy2026-p09-ef-water.pdf',
         'expenses/glytdbud-expense-fy2026-p09-ef-water.txt',
         "Water enterprise fund spending against budget, FY2026 through 31 March 2026 — MUNIS "
         "year-to-date budget report (records request, August 2026)"),
        ('revenue/glytdbud-revenue-fy2026-p09-ef-water.pdf',
         'revenue/glytdbud-revenue-fy2026-p09-ef-water.txt',
         "Water enterprise fund revenue against budget, FY2026 through 31 March 2026 — MUNIS "
         "year-to-date budget report (records request, August 2026)"),
        ('expenses/glytdbud-expense-fy2026-p09-ef-sewer.pdf',
         'expenses/glytdbud-expense-fy2026-p09-ef-sewer.txt',
         "Sewer enterprise fund spending against budget, FY2026 through 31 March 2026 — MUNIS "
         "year-to-date budget report (records request, August 2026)"),
        ('revenue/glytdbud-revenue-fy2026-p09-ef-sewer.pdf',
         'revenue/glytdbud-revenue-fy2026-p09-ef-sewer.txt',
         "Sewer enterprise fund revenue against budget, FY2026 through 31 March 2026 — MUNIS "
         "year-to-date budget report (records request, August 2026)"),
        ('expenses/glytdbud-expense-fy2026-p09-ef-solid-waste.pdf',
         'expenses/glytdbud-expense-fy2026-p09-ef-solid-waste.txt',
         "Solid waste enterprise fund spending against budget, FY2026 through 31 March 2026 — "
         "MUNIS year-to-date budget report (records request, August 2026)"),
        ('revenue/glytdbud-revenue-fy2026-p09-ef-solid-waste.pdf',
         'revenue/glytdbud-revenue-fy2026-p09-ef-solid-waste.txt',
         "Solid waste enterprise fund revenue against budget, FY2026 through 31 March 2026 — "
         "MUNIS year-to-date budget report (records request, August 2026)"),
        ('expenses/glytdbud-expense-fy2026-p09-ef-peg-access.pdf',
         'expenses/glytdbud-expense-fy2026-p09-ef-peg-access.txt',
         "Cable and broadband (PEG access) enterprise fund spending against budget, FY2026 "
         "through 31 March 2026 — MUNIS year-to-date budget report (records request, August 2026)"),
        ('revenue/glytdbud-revenue-fy2026-p09-ef-peg-access.pdf',
         'revenue/glytdbud-revenue-fy2026-p09-ef-peg-access.txt',
         "Cable and broadband (PEG access) enterprise fund revenue against budget, FY2026 "
         "through 31 March 2026 — MUNIS year-to-date budget report (records request, August 2026)"),
        # The August 2025 Parks & Recreation delivery. THE DOCUMENT THIS WHOLE SCRIPT IS FOR
        # is the first of these, and its label carries the town's own filename for it.
        ('purchase-orders/po-closed-fy2025-parks-grounds-bid.pdf',
         'purchase-orders/po-closed-fy2025-parks-grounds-bid.txt',
         "Parks grounds maintenance bid, year one from 1 July 2024 — mowing, weeding, turf, "
         "clean-ups and infield work priced per park (Fitzgerald, McNally, Marshall, Memorial, "
         "Town Beach, Wallis); the town's own filename is “Landscaping Costs.pdf” "
         "(records request, August 2025)"),
        ('account-details/parks-program-financials-fy2025-myrec.pdf',
         'account-details/parks-program-financials-fy2025-myrec.txt',
         "Parks & Recreation programme sales, FY2025 — registrations and fees programme by "
         "programme, resident and non-resident, from the MyRec registration system "
         "(records request, August 2025)"),
        ('account-details/parks-membership-sales-fy2025-myrec.pdf',
         'account-details/parks-membership-sales-fy2025-myrec.txt',
         "Beach passes sold, FY2025 — counts and receipts by pass type, resident and "
         "non-resident, from the MyRec registration system (records request, August 2025)"),
        ('account-details/parks-program-offerings-fy2025-myrec.pdf',
         'account-details/parks-program-offerings-fy2025-myrec.txt',
         "Every Parks & Recreation programme offered in FY2025 as the public saw it — "
         "description, sessions, ages and fee, 32 pages (records request, August 2025)"),
        # Our provenance notes. Below the line (rule 3): we wrote them, and the label says so.
        # They are indexed because they are where a publisher's filename, a request date and
        # a grade of evidence are written down -- which is exactly what somebody looking for
        # a document searches by.
        ('account-details/PROVENANCE-parks-2025.md', 'account-details/PROVENANCE-parks-2025.md',
         "Where the August 2025 Parks & Recreation records request came from — the town's own "
         "filename for each of the six documents, including “Landscaping Costs.pdf”, "
         "and which are system printouts (our provenance note)"),
        ('account-details/PROVENANCE-fund1301.md', 'account-details/PROVENANCE-fund1301.md',
         "Where the June 2026 athletics records request came from, what was asked for, and what "
         "each workbook actually holds (our provenance note)"),
        ('account-details/PROVENANCE-field-rental-lysa.md',
         'account-details/PROVENANCE-field-rental-lysa.md',
         "Where the Lunenburg Youth Soccer field rental receipts came from, and which fund the "
         "money lands in (our provenance note)"),
        ('expenses/PROVENANCE-fy2026-p09.md', 'expenses/PROVENANCE-fy2026-p09.md',
         "Where the FY2026 period 9 quarterly reports came from, and what is bounded rather than "
         "known about the request (our provenance note)"),
        ('expenses/PROVENANCE-fy2026-p12.md', 'expenses/PROVENANCE-fy2026-p12.md',
         "Where the FY2026 period 12 year-to-date budget report came from, and why period 12 is "
         "not the year-end close (our provenance note)"),
        ('revenue/PROVENANCE-fy2026-p09.md', 'revenue/PROVENANCE-fy2026-p09.md',
         "Where the FY2026 period 9 revenue reports came from — points to the note beside the "
         "expenditure reports (our provenance note)"),
        ('fund-balances/PROVENANCE-fy2026-p09.md', 'fund-balances/PROVENANCE-fy2026-p09.md',
         "Where the FY2026 period 9 fund balance reports came from — points to the note beside "
         "the expenditure reports (our provenance note)"),
        ('purchase-orders/PROVENANCE-parks-grounds-bid.md',
         'purchase-orders/PROVENANCE-parks-grounds-bid.md',
         "Where the Parks grounds maintenance bid came from, and what a bid is and is not "
         "(our provenance note)"),
    ],
    'correspondence': [
        ('2024-03-01-parks-beach-and-swim-fees.txt', '2024-03-01-parks-beach-and-swim-fees.txt',
         "Beach pass and swim lesson fees the Parks Commission voted, 1 March 2024 — an internal "
         "town email (records request, August 2025)"),
        ('2025-05-bus-fees-superintendent.txt', '2025-05-bus-fees-superintendent.txt',
         "School bus fees for 2025-26, May 2025 — email from the Superintendent "
         "(from the recipient's inbox, August 2026)"),
        ('2026-08-17-bus-routes-and-fees-superintendent.txt',
         '2026-08-17-bus-routes-and-fees-superintendent.txt',
         "School bus routes and fees for 2026-27, 17 August 2026 — email from the Superintendent "
         "(from the recipient's inbox, August 2026)"),
        ('2026-09-18-school-field-maintenance-superintendent.txt',
         '2026-09-18-school-field-maintenance-superintendent.txt',
         "What the schools say maintaining the sports fields and grounds costs — an email "
         "exchange with the Superintendent (forwarded to this archive, 18 September 2026)"),
        ('2026-03-30-ski-coop-invoice.md', '2026-03-30-ski-coop-invoice.md',
         "How the ski co-op invoice reached us, what it shows about what Lunenburg bills "
         "Littleton, Narragansett and Leominster, and what it does not show "
         "(our provenance note)"),
    ],
}


def sha_and_bytes(path):
    h = hashlib.sha256()
    n = 0
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
            n += len(chunk)
    return n, h.hexdigest()


def rows_for(folder):
    """One row per document, with bytes and sha256 READ OFF THE FILE.

    A document with no original (`local` empty) is sized by its text, because that is the
    only copy there is; everything else is sized by the original, which is what `local`
    names and what `/docs/` serves.
    """
    out, problems = [], []
    for local, text, label in TREES[folder]:
        textp = os.path.join(SRC, folder, text) if text else ''
        localp = os.path.join(SRC, folder, local) if local else ''
        if local and not os.path.exists(localp):
            problems.append('%s/%s — catalogued but not on disk' % (folder, local))
            continue
        if not text or not os.path.exists(textp):
            problems.append('%s/%s — no extracted text on disk' % (folder, text or local))
            continue
        sized = localp or textp
        n, sha = sha_and_bytes(sized)
        key = '%s/%s' % (folder, local) if local else None
        upstream = B.SOURCE_URLS.get(key, '') if key else ''
        if folder == 'contracts' and text == 'txt/lea-teachers-2024-2027.txt':
            upstream = LEA_DISTRICT_COPY
        out.append({
            'label': label,
            'upstream': upstream,
            'local': 'sources/%s/%s' % (folder, local) if local else '',
            'text': 'sources/%s/%s' % (folder, text),
            'bytes': n,
            'sha256': sha,
            'read': 'had it',
        })
    return out, problems


def render(rows):
    buf = io.StringIO(newline='')
    w = csv.DictWriter(buf, fieldnames=HEADER, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    stale, allprob, total = [], [], 0
    for folder in sorted(TREES):
        rows, problems = rows_for(folder)
        allprob += problems
        total += len(rows)
        path = os.path.join(SRC, folder, 'index.csv')
        text = render(rows)
        have = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if args.check:
            if have != text:
                stale.append(path)
        elif have != text:
            with open(path, 'w', encoding='utf-8', newline='') as fh:
                fh.write(text)
        withurl = sum(1 for r in rows if r['upstream'])
        print('%-16s %2d rows, %2d with a publisher URL, %2d addressed in the label only'
              % (folder, len(rows), withurl, len(rows) - withurl))
    print('%d rows in 4 trees' % total)
    for p in allprob:
        print('  NOT CATALOGUED: ' + p)
    if args.check and stale:
        sys.exit('stale:\n  ' + '\n  '.join(stale))


if __name__ == '__main__':
    main()
