#!/usr/bin/env python3
"""What kind of job each printed roster title is, and which grade if it says.

    python3 scripts/classify_roster_roles.py [--check]

Writes `sources/data/role-classification.csv`.

WHY A DICTIONARY AND NOT A COLUMN

The rosters print a job title and a section heading, and nothing else. `Para`, `(para)`,
`Paraprofessional`, `Paraprotessional`, `Tutor`, `Aide`, `Teaching Asst.` are the same job
across fifteen years of changing house style, and 1,537 of 3,815 rows print no title at all
— for those the section heading is the only signal there is.

So this classifies the VOCABULARY, not the rows: one entry per distinct
(role_raw, grade_or_dept) pair, with the rule that decided it. 1,021 pairs, which a person
can read. It joins back to the rows in SQL, it survives the rosters being re-extracted, and
a wrong call is one line to fix rather than a rerun of anything.

**THIS IS OUR INFERENCE AND IT IS NOT THE DOCUMENT.** `role_raw` is what the town printed;
`role_category` is what we think that means. They are separate columns for the same reason
rule 7 exists — a real measurement and a plausible explanation must never be the same
field. Where nothing decides it, the answer is `unknown`, never a guess: 40% of these rows
have no printed title, and quietly calling them all teachers would produce a clean-looking
table that is mostly invention.

The existing `position` column has already shown what happens when a classification is
trusted without its evidence beside it: it reads 0, 5, 4, 4, 0 for the Kindergarten aides
of FY2011–FY2015, and two of those zeros are a printing change rather than a staffing one.
`classified_by` names the rule for every row so the same failure is visible next time.
"""
import argparse
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'data', 'staff-roster-entries.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'role-classification.csv')

# Ordered. The FIRST rule that matches wins, so the specific ones come before the general:
# "speech" before "teacher", "assistant principal" before "principal". Each rule is
# (category, name, pattern) and the name travels with every row it decides.
RULES = [
    ('paraprofessional', 'para-title',
     r'\bpara(?:professional|protessional|prof|pro)?\b|\(para\)|^para$'),
    ('paraprofessional', 'aide-title', r'\b(?:teaching|teacher|classroom|instructional)\s+'
                                       r'ass?is?t|teaching\s+asst|\baides?\b|\bt\.?a\.?\b'),
    ('paraprofessional', 'tutor-title', r'\btutors?\b'),
    ('administrator', 'principal', r'\bprincipal\b|\bheadmaster\b'),
    ('administrator', 'superintendent', r'\bsuperintendent\b'),
    ('administrator', 'director', r'\bdirector\b|\bcoordinator\b|\bsupervisor\b'
                                  r'|\bdept\.?\s*(?:head|liaison)\b|\bdh\b|\bteam leader\b'),
    ('administrator', 'business-office', r'\bbusiness\s+(?:manager|administrator)\b'
                                         r'|\btreasurer\b|\bpayroll\b'),
    ('nurse', 'nurse', r'\bnurse\b|\brn\b|\bhealth\s+(?:aide|assistant)\b'),
    ('social_worker', 'social-worker', r'\bsocial\s+work|\bl?icsw\b|\blcsw\b|\bmsw\b'),
    ('psychologist', 'psychologist', r'\bpsycholog|\bschool\s+psych'),
    ('counselor', 'counselor', r'\bcounsel|\bguidance\b|\badjustment\b'),
    ('speech_therapist', 'speech', r'\bspeech\b|\bslp\b|\blanguage\s+patholog'),
    ('therapist', 'ot-pt', r'\boccupational\s+therap|\bphysical\s+therap|\bcota\b|\bot\b|\bpt\b'),
    ('librarian', 'library', r'\blibrar|\bmedia\s+special'),
    ('custodian', 'custodial', r'\bcustod|\bjanitor|\bmaintenance\b|\bgrounds\b'),
    ('cafeteria', 'food-service', r'\bcafeteria\b|\bfood\s+serv|\bkitchen\b|\bcook\b|\blunch\b'),
    ('secretary', 'clerical', r'\bsecretar|\bclerk\b|\breceptionist\b|\badmin\.?\s+ass?is?t'),
    ('technology', 'technology', r'\btechnolog|\bcomputer\b|\bnetwork\b|\bit\s+special'),
    ('coach', 'athletics', r'\bcoach\b|\bathletic\s+(?:director|trainer)\b'),
    ('specialist', 'interventionist', r'\bspecialist\b|\bintervention|\breading\s+recovery\b'
                                      r'|\bbcba\b|\banalyst\b'),
    ('teacher', 'teacher-title', r'\bteacher\b|\binstructor\b|\bfaculty\b'),
]

# When the title is blank the section heading is all there is. These read a HEADING, which
# is weaker evidence than a title and is recorded as such in `classified_by`.
HEADING_RULES = [
    ('paraprofessional', 'heading-paras', r'\bparaprofessional|\bparas\b|\baides\b|\btutors\b'),
    ('cafeteria', 'heading-cafeteria', r'\bcafeteria\b|\bfood\s+serv|\bkitchen\b'),
    ('custodian', 'heading-custodial', r'\bcustod|\bmaintenance\b|\bgrounds\b'),
    ('nurse', 'heading-nurse', r'\bnurs'),
    ('secretary', 'heading-clerical', r'\bsecretar|\boffice\s+staff\b'),
    ('administrator', 'heading-admin', r'\badministration\b|\bcentral\s+office\b'),
    ('counselor', 'heading-guidance', r'\bguidance\b|\bcounsel'),
    ('technology', 'heading-technology', r'\btechnolog|\bit\b|\bcomputer\b'),
    ('specialist', 'heading-specialists', r'\bspecialists?\b|\bintervention'),
    ('specialist', 'heading-special-services', r'\bspecial\s+(?:services|education)\b'
                                               r'|\bsped\b|\bachieve\b|\btlc\b|\bmitss\b'),
    # An academic department heading with no title under it is a teaching post. This is
    # the weakest inference here and it is named so it can be argued with.
    ('teacher', 'heading-department',
     r'\b(?:english|language arts|math|science|social studies|history|foreign language'
     r'|world language|unified arts|art|music|physical education|health|business'
     r'|technology education|reading|grade\s*\d|grades?\b|kindergarten|pre-?school'
     r'|special areas|ell|esl|team)\b'),
]

GRADE_PATTERNS = [
    ('PK', r'\bpre-?k\b|\bpre-?school\b|\bpreschool\b|\bintegrated\s+pre'),
    ('K', r'\bkindergarten\b|\bkdg\b|(?<![a-z])k(?:[1-9]\b|\s*-|\b)'),
]
ORDINALS = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5, 'sixth': 6,
            'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10, 'eleventh': 11,
            'twelfth': 12}


def grade_of(text):
    """The grade a title or heading names, or '' — never a guess.

    `Gr. 3 Para`, `Grade 8 Tutor`, `3A`, `Second Grade Teachers`, `Kindergarten` all name
    one. Most rows name none, and that is the answer for them.
    """
    t = text.lower()
    for label, pat in GRADE_PATTERNS:
        if re.search(pat, t):
            return label
    m = re.search(r'\bgr(?:ade)?s?\.?\s*(\d{1,2})\b', t)
    if m and 1 <= int(m.group(1)) <= 12:
        return str(int(m.group(1)))
    m = re.search(r'\b(' + '|'.join(ORDINALS) + r')\s+grade\b', t)
    if m:
        return str(ORDINALS[m.group(1)])
    # `3A`, `5B` — a classroom label, used at the elementary schools.
    m = re.search(r'^\s*(\d{1,2})\s*[a-e]\s*$', t)
    if m and 1 <= int(m.group(1)) <= 12:
        return str(int(m.group(1)))
    return ''


def classify(role_raw, heading):
    role, head = (role_raw or '').strip(), (heading or '').strip()
    for cat, name, pat in RULES:
        if role and re.search(pat, role.lower()):
            return cat, name
    # The heading is tried whether or not there is a title, not only when the title is
    # blank. The middle school prints team names in the title column -- `Red`, `Blue`,
    # `White` under `Grade 7` -- so a row can have a title that names no job at all while
    # its heading says exactly what the job is. `classified_by` records that the evidence
    # was the heading, which is weaker, so a reader can weigh it.
    for cat, name, pat in HEADING_RULES:
        if re.search(pat, head.lower()):
            return cat, name
    # A title we do not recognise. Said, not guessed.
    return 'unknown', 'no-rule-matched'


def build():
    with open(SRC, newline='') as fh:
        rows = list(csv.DictReader(fh))
    pairs = collections.Counter(
        ((r.get('role_raw') or '').strip(), (r.get('grade_or_dept') or '').strip())
        for r in rows)
    out = []
    for (role, head), n in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0])):
        cat, rule = classify(role, head)
        # A grade printed on the title beats one on the heading: the heading is the
        # section, the title is the post.
        grade = grade_of(role) or grade_of(head)
        out.append(dict(role_raw=role, grade_or_dept=head, rows=n,
                        role_category=cat, role_grade=grade, classified_by=rule))
    return rows, out


CAVEAT_OUT = os.path.join(ROOT, 'sources', 'data', 'role-classification-caveat.txt')


def caveat(rows, table):
    """The caveat, with its figures DERIVED rather than typed.

    The first version of this sentence said the kindergarten series reads "0, 5, 4, 4, 0"
    for FY2011-FY2015. Two of those five numbers were wrong. They came from the old
    `position` field, and the classification shipped in the same commit already recovered
    FY2011 (printed "Teaching Asst.") and FY2014 (one row printed "Paraprotessional") --
    so the caveat repeated the undercount it existed to explain, and an assistant reading
    the rows caught it.

    That is rule 2 with the stakes at their highest: a figure typed into a sentence is the
    only thing here that can be silently wrong, and a figure typed into a CAVEAT is wrong
    in the place a reader is least able to check it. So the series is computed from the
    same dictionary this script writes, every time.
    """
    look = {(r['role_raw'], r['grade_or_dept']): r for r in table}
    series = {}
    for r in rows:
        c = look.get(((r.get('role_raw') or '').strip(),
                      (r.get('grade_or_dept') or '').strip()))
        if c and c['role_category'] == 'paraprofessional' and c['role_grade'] == 'K':
            series[r['fy']] = series.get(r['fy'], 0) + 1
    years = sorted({r['fy'] for r in rows})
    counts = [series.get(y, 0) for y in years]
    zeros = [y for y, n in zip(years, counts) if n == 0]
    return (
        'POSITION IS A CLASSIFICATION AND THE PRINTING IT READS CHANGES. The town has '
        'called the same job Tutor, Aide, Tutors/Aides, Paraprofessional, Para, (para) '
        'and Sped Para across fifteen years, and once "Paraprotessional", an OCR typo. '
        '`role_category` in `role-classification.csv` absorbs that; the raw `position` '
        'column does not, and undercounts wherever the house style moved.\n\n'
        'Counting paraprofessionals in the Kindergarten section by `role_category` gives '
        + ', '.join(f'FY{y} {n}' for y, n in zip(years, counts)) + '.\n\n'
        'THE ZEROS ARE EXTRACTION FAILURES, NOT STAFFING'
        + (f' ({", ".join("FY" + y for y in zeros)})' if zeros else '')
        + '. FY2015 printed the page in two columns and the extractor collapsed it, '
        'leaving five people with no title and their names shifted by one row against '
        'their posts. FY2024 lists the Primary School paraprofessionals in one '
        'undifferentiated column with no section at all, and FY2025 groups them by '
        'programme rather than grade. A series run to FY2025 will read as a collapse in '
        'kindergarten support that did not happen. Use `role_raw`, which is what the '
        'report actually printed, before trusting any of it.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    rows, table = build()
    cols = ['role_raw', 'grade_or_dept', 'rows', 'role_category', 'role_grade',
            'classified_by']
    body = ','.join(cols) + '\n'
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in table:
        w.writerow(r)
    body = buf.getvalue()

    if args.check:
        # newline='' : the CSV writer emits \r\n, and reading without this translates it
        # to \n, so the comparison was off by exactly one byte per line -- 1,031 of them --
        # and reported a file as stale every single run. A check that always fails is a
        # check nobody reads.
        current = (open(OUT, newline='').read() if os.path.exists(OUT) else '')
        if current != body:
            print('STALE  role-classification.csv — run: '
                  'python3 scripts/classify_roster_roles.py')
            return 1
        print('ok: role-classification.csv matches the rosters')
        return 0

    with open(OUT, 'w', newline='') as fh:
        fh.write(body)
    with open(CAVEAT_OUT, 'w') as fh:
        fh.write(caveat(rows, table) + '\n')

    covered = sum(r['rows'] for r in table if r['role_category'] != 'unknown')
    total = sum(r['rows'] for r in table)
    graded = sum(r['rows'] for r in table if r['role_grade'])
    print(f'{len(table):,} distinct (title, heading) pairs over {total:,} roster rows')
    print(f'  classified   {covered:,} rows ({covered / total:.0%})')
    print(f'  grade named  {graded:,} rows ({graded / total:.0%})')
    print()
    by = collections.Counter()
    for r in table:
        by[r['role_category']] += r['rows']
    for cat, n in by.most_common():
        print(f'  {cat:20s} {n:>5,}')
    unknown = [r for r in table if r['role_category'] == 'unknown']
    if unknown:
        print(f'\nthe {len(unknown)} unclassified pairs, largest first — these are the '
              f'ones to argue with:')
        for r in sorted(unknown, key=lambda r: -r['rows'])[:12]:
            print(f'  {r["rows"]:>4}  title={r["role_raw"][:28]!r:32} '
                  f'heading={r["grade_or_dept"][:28]!r}')
    print(f'\nwrote {os.path.relpath(OUT, ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
