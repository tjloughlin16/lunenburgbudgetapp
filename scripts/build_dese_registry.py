#!/usr/bin/env python3
"""Every DESE source, its address, and how to fetch it again next year.

    python3 scripts/build_dese_registry.py           # rewrite from what is on disk
    python3 scripts/build_dese_registry.py --check   # fail if it no longer reproduces

WHY THIS EXISTS SEPARATELY FROM THE ARCHIVE MANIFEST

`archive-manifest.csv` records what we HOLD. This records HOW TO GET IT AGAIN. Those are
different questions and only one of them survives a year.

TJ: *"These dashboards and resources are critical, and we can go back every year."* That is
the requirement — an annual refresh, done by somebody who was not here when the files were
found. So every row carries the address a human opens, the address a program fetches, and
the sha256 of what we got, and the rows are not deleted when superseded.

**THREE ADDRESSES, NOT ONE, AND THEY ARE NOT INTERCHANGEABLE.** This bit was learned the
hard way today:

  portal_page   what a person opens in a browser
  api_endpoint  what a program fetches. Socrata only; blank where none exists
  publisher     the page DESE actually sends you to

`qt58-634r` is the cautionary case. Its Socrata page carries NO DOWNLOAD and redirects to
`doe.mass.edu/finance/chapter70/`, which is a different site with a different publication
cycle. A registry that recorded only the Socrata id would send next year's refresh to a
dead end. So `source_kind` distinguishes them and `refresh_note` says what to do.

**AND THE FILE FORMAT IS PART OF THE ADDRESS.** The Chapter 70 workbooks are interactive:
the front sheet is a VLOOKUP interface that reads as empty or as formula text, and the data
sits in sheets behind it. Recorded per row, because rediscovering it costs an hour.
"""
import argparse
import csv
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'dese-source-registry.csv')
FIELDS = ['name', 'source_kind', 'dataset_id', 'portal_page', 'api_endpoint', 'publisher',
          'local', 'bytes', 'sha256', 'offers', 'refresh_note']

SOCRATA = 'https://educationtocareer.data.mass.gov'

# (local file, dataset id, name, what it offers, refresh note)
SOURCES = [
    # --- Socrata: the portal export and the API return identical bytes (verified) -------
    ('sources/state-dese/district-expenditures-by-function.xlsx', 'cnfs-edqq',
     'District Expenditures by Function Code',
     'GEN_FUND and GRNTS_REVOLV separately, by function code, per district, 2009-2025. '
     'The fund split rule 11 says nobody publishes.', ''),
    ('sources/state-dese/district-expenditures-by-spending-category.xlsx', 'er3w-dyti',
     'District Expenditures by Spending Category',
     'Supersedes dese_measure on coverage: 421 districts against 7, and agrees with it '
     'exactly where they overlap.', ''),
    ('sources/state-dese/school-expenditures-by-spending-category.xlsx', 'i5up-aez6',
     'School Expenditures by Spending Category',
     'Per-SCHOOL spending. The only per-school financial series in this archive.', ''),
    ('sources/inbox/dese-residents-sending.xlsx', 'vxt3-k35x',
     'Where Residents Go to School (Sending)',
     'Where resident children go, by receiving district and reason, 2014-2026. Closes '
     '"how many children leave and for where".', ''),
    ('sources/inbox/dese-enrollment-receiving.xlsx', '8xyg-59b2',
     'Reasons for Student Enrollment by Town (Receiving)',
     'Who arrives and from where. The mirror of the sending file; together they give a '
     'NET choice position.', ''),
    ('sources/inbox/dese-circuit-breaker.xlsx', 'ab34-d3ma',
     'Special Education Circuit Breaker Reimbursements',
     'A fund rule 11 names as unmapped, AND a count of children: ELIG_STU_CLAIM_CNT.',
     'Keys on FY, not SY. Every other file here is school year.'),
    ('sources/inbox/dese-ch70-foundation-nss.xlsx', '5izv-jyrd',
     'Chapter 70 Foundation Budget and Net School Spending',
     'Required against actual net school spending. Lunenburg sits at ~128% of the floor.',
     'Stops at SY2022. The Chapter 70 profile workbook below runs to FY2026.'),
    ('sources/inbox/dese-teachers-by-grade-subject.xlsx', '77fu-a6h8',
     'Elementary and Secondary Teachers by Grade and Subject',
     'FTE by grade band AND subject AND school. Breaks a limit recorded as structural: '
     'grade detail without FTE, or FTE without grade detail, never both.',
     'Carries a State row and a SUBJ of All beside detail. Establish levels before summing.'),
    ('sources/inbox/dese-teachers-by-program-area.xlsx', 'vd2f-ib9q',
     'Elementary and Secondary Teachers by Program Area',
     'GEN_ED / SPED / CAREER_TECH / EL teacher FTE, per school.',
     'Lunenburg SPED FTE falls 18.5 (2008) to 2.0 (2026) while total FTE holds flat. That '
     'is the signature of recoding, not of staff leaving. UNRESOLVED.'),
    ('sources/inbox/dese-teacher-data.xlsx', '4684-cw3t',
     'Elementary and Secondary Teacher Data',
     'Teacher counts, student-teacher ratio, licensure, experience, in-field share.', ''),
    ('sources/inbox/dese-educators-retention.xlsx', 'fz9c-2g33',
     'Total Educators, Retention, and New Hires',
     'Headcount by job class INCLUDING Administrator and Paraprofessional, plus hires and '
     'retention. 2021-2023 only.',
     'Headcount, not FTE. Administrators 28->38 over three years on a base of ten people; '
     'a reclassification would look identical.'),
    ('sources/inbox/dese-sped-indicators.xlsx', 'yamx-769q',
     'Special Education Indicators',
     'A published COUNT of students with disabilities, 217-265, plus sped staffing ratios.',
     'Its paraprofessional ratio times the count implies $69,161 per FTE against the '
     'district budget line. The two are not the same population. UNRESOLVED.'),
    ('sources/inbox/dese-sped-program-characteristics.xlsx', 'n62c-bx65',
     'Special Education Program Characteristics and Student Demographics',
     'Disability type and demographics behind the SWD count.', ''),
    ('sources/inbox/dese-sped-placement-trajectory.xlsx', '92x3-2qj9',
     'Special Education Placement Trajectory',
     'Where a child starts against where they end up. The route into out-of-district.',
     'Tiny bases. 14.3% of 28 is four children; the percentage must never travel alone.'),
    ('sources/inbox/dese-sped-movement.xlsx', '8aww-sugs',
     'Students Moving In and Out of Special Education Services',
     'Caseload dynamics: how many enter and leave services each year.',
     'SY2024 and SY2025 are identical across all four columns. Probably a carried-forward '
     'row; check before quoting either.'),
    ('sources/inbox/dese-enrollment-by-grade.xlsx', 't8td-gens',
     'Enrollment: Grade, Race/Ethnicity, Gender, and Selected Populations',
     'Enrolment by grade and school. The denominators for most of the above.', ''),
]

# Sources that are NOT on the Socrata portal. The distinction is the point.
ELSEWHERE = [
    ('sources/inbox/dese-ch70-district-profile.xlsx', 'qt58-634r',
     'Chapter 70 District Profile',
     'https://www.doe.mass.edu/finance/chapter70/',
     '34 years of the Chapter 70 formula, FY1993-FY2026 — foundation enrolment, foundation '
     'budget, required local contribution, aid, required and actual NSS. FY2026 aid '
     'reconciles exactly to the figure derived independently for /state-aid.',
     'The Socrata page qt58-634r has NO DOWNLOAD and redirects here. Read with '
     'data_only=True and take the DataC70 sheet; the front sheet is a VLOOKUP interface.'),
    ('sources/inbox/dese-ch70-key-factors.xlsx', '',
     'Chapter 70 Key Factors',
     'https://www.doe.mass.edu/finance/chapter70/',
     'Foundation enrolment split by English learner, vocational and low-income share — the '
     'formula INPUTS, which is what lets anybody model how it responds to enrolment change.',
     'Data sheets are dataAid, dataNSS, dataContribution. Front sheet is an interface.'),
    ('sources/inbox/dese-job-classification-codes.docx', '',
     'Job Classification Codes (evaluation)',
     'https://www.doe.mass.edu/',
     '43 code/label pairs -- 1200 Superintendent, 1305 Principal and so on. The vocabulary '
     'behind EPIMS job classification.',
     'Covers the EVALUATION job classes: administrators and licensed staff. Contains NO '
     'paraprofessional codes, so it does not by itself resolve the paraprofessional '
     'boundary.'),
    ('sources/inbox/sims-datahandbook-current.docx', '',
     'SIMS Data Handbook (current)',
     'https://www.doe.mass.edu/',
     'Defines STUDENT data: special education placement, school choice. 42 mentions of '
     'special education, 6 of placement.',
     'Contains NO staffing definitions — checked with word boundaries after raw substring '
     'counts said otherwise. The staffing definitions are in EPIMS, which is NOT YET HELD '
     'and is what would resolve both open contradictions.'),
    ('sources/inbox/epims-datahandbook.docx', '', 'EPIMS Data Handbook',
     'https://www.doe.mass.edu/',
     'RESOLVES the paraprofessional contradiction: FTE is per ASSIGNMENT, not per person, '
     'so DESE FTE and the district budget line have different denominators. AND reveals '
     'that EPIMS collects per-individual Federal Salary Source plus percent of salary — '
     'which fund pays which post, the thing rule 11 says nobody publishes.',
     'Federal grants only; state grants and revolving funds are not in these fields.'),
    ('sources/inbox/sims-datahandbook_2021.docx', '', 'SIMS Data Handbook 2021',
     'https://www.doe.mass.edu/', 'As above, 2021 edition.', ''),
    ('sources/inbox/sims-datahandbook_2022.docx', '', 'SIMS Data Handbook 2022',
     'https://www.doe.mass.edu/', 'As above, 2022 edition.', ''),
]

# Named, wanted, not yet held. A registry that only lists what arrived cannot tell the next
# person what was looked for and missed.
WANTED = [
    ('EPIMS federal salary source, aggregated by job classification',
     'records request — Lunenburg Public Schools',
     'EPIMS collects per-individual federal grant funding percentages. Aggregated by job '
     'classification this answers which fund pays which post — rule 11 outright. No '
     'individual records sought.'),
    ('Non-Public School Enrollment', SOCRATA + '/d/cbbr-jpy4',
     'Children leaving to PRIVATE school. The choice files capture public-to-public only, '
     'so this is the missing half of who leaves.'),
    ('Class Size', SOCRATA + '/d/35yv-uxv5',
     'What staffing changes did to classrooms — the thing residents actually feel.'),
    ('Mental Health Staff by District', SOCRATA + '/d/fthb-bpav',
     'The town cut a school psychologist to zero; this is that category.'),
    ('Educators by Age Group', SOCRATA + '/d/a4b4-k49f',
     'Retirement exposure, which drives salary-step cost.'),
    ('Collaborative Placement', SOCRATA + '/d/irbh-xf6w',
     'Collaborative is one of the three out-of-district categories in our placement counts.'),
]


def sha(path):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return '', 0
    h = hashlib.sha256()
    with open(full, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest(), os.path.getsize(full)


def build():
    rows = []
    for local, did, name, offers, note in SOURCES:
        s, n = sha(local)
        rows.append(dict(name=name, source_kind='socrata', dataset_id=did,
                         portal_page=f'{SOCRATA}/d/{did}',
                         api_endpoint=f'{SOCRATA}/api/v3/views/{did}/query.json',
                         publisher=SOCRATA, local=local, bytes=n, sha256=s,
                         offers=offers, refresh_note=note))
    for local, did, name, pub, offers, note in ELSEWHERE:
        s, n = sha(local)
        rows.append(dict(name=name, source_kind='doe.mass.edu', dataset_id=did,
                         portal_page=(f'{SOCRATA}/d/{did}' if did else ''),
                         api_endpoint='', publisher=pub, local=local, bytes=n,
                         sha256=s, offers=offers, refresh_note=note))
    for name, where, offers in WANTED:
        rows.append(dict(name=name, source_kind='WANTED', dataset_id='', portal_page=where,
                         api_endpoint='', publisher='', local='', bytes=0, sha256='',
                         offers=offers, refresh_note='Not yet held.'))

    missing = [r['name'] for r in rows
               if r['source_kind'] != 'WANTED' and not r['sha256']]
    if missing:
        raise SystemExit(
            'these registry rows name a file that is not on disk:\n  '
            + '\n  '.join(missing)
            + '\nA registry that points at nothing is worse than no registry: it reads as '
              'coverage. Fix the path or remove the row.')
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader(); w.writerows(rows)
    text = buf.getvalue()

    if a.check:
        # newline='' on BOTH sides. csv writes \r\n; a text-mode read translates it to
        # \n, so comparing the two reports a clean file as stale every single time. This
        # repo has had that exact bug before -- check_generated.py's docstring records it
        # -- and I reproduced it here within the hour.
        have = (open(OUT, encoding='utf-8', newline='').read()
                if os.path.exists(OUT) else '')
        if have != text:
            print('STALE — %s no longer reproduces' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %d DESE sources registered, %d of them still wanted'
              % (len(rows), sum(1 for r in rows if r['source_kind'] == 'WANTED')))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8', newline='').write(text)
    held = [r for r in rows if r['source_kind'] != 'WANTED']
    print('wrote %s — %d sources held (%.0f MB), %d named and wanted'
          % (os.path.relpath(OUT, ROOT), len(held),
             sum(r['bytes'] for r in held) / 1e6,
             len(rows) - len(held)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
