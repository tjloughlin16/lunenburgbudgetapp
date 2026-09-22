#!/usr/bin/env python3
"""Who SIGNED each department's report — the head of every body, every year.

    python3 scripts/extract_report_signatures.py [--check]

Writes `sources/data/report-signatures.csv`.

TJ, 22 September 2026, on being told the district publishes no top layer after FY2022:
*"red flag: Central Office in 8 of 15 years, Superintendent named only in FY2011-12. I bet
you this isn't true."*

IT WAS NOT TRUE, AND IT WAS RULE 13c AGAIN. The Superintendent is named in every single
year — Loxi Jo Calmes, then Sheila M. Harrity, then Dr. Kate Burnham, then Dr. Jodi
Fortuna — and the claim was a fact about OUR EXTRACTOR: it reads per-school roster TABLES
and never the block that ends each report.

    Respectfully submitted,
    Sheila M. Harrity, Ed.D.
    Superintendent

Nearly every department report ends that way. 730 of them across fifteen books, and they
are the one place the town names the person in charge of a body that publishes no roster
at all — the Library, the Town Clerk, Conservation, the Sewer Commission.

THE PAGE RANGE COMES FROM THE TOWN'S OWN CONTENTS PAGE (`extract_report_index.py`), so a
signature is attributed to the department whose report it ends rather than to whichever
heading happened to be above it. That was the other half of the same bug.

A TRAP WORTH KNOWING: `Thomas R. Browne, Superintendent-Director` signs the Montachusett
Regional report inside Lunenburg's book. He is a different district's superintendent, and
a reader who joins on the title alone gets him as Lunenburg's.
"""
import argparse
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')
INDEX = os.path.join(DATA, 'report-index.csv')
OUT = os.path.join(DATA, 'report-signatures.csv')
FIELDS = ['fy', 'department', 'person', 'title', 'page', 'as_printed']

SIG = re.compile(r'respectfully submitted|submitted by|sincerely(?: yours)?', re.I)
HEADING = re.compile(r"^[A-Z][A-Z &/'.\-]{6,}$")
# A person: two-to-four capitalised words, allowing an initial, a suffix and a prefix.
# A RANK IN FRONT OF THE NAME IS STILL A NAME. `Chief James P. Marino` and `Chief Thomas
# L. Gammel` sign the Police and Fire reports, and testing the whole head for title words
# threw both away. And `T.J. Blauser` needs initials that carry their own dots.
RANK = re.compile(r"^(?:Dr|Mr|Mrs|Ms|Rev|Chief|Deputy Chief|Lt|Lieutenant|Sgt|Sergeant|"
                  r"Capt|Captain|Supt|Superintendent)\.?\s+", re.I)
PERSON = re.compile(
    r"^([A-Z][A-Za-z'\-]*\.?(?:[A-Z]\.)*(?:\s+(?:[A-Z]\.?|[A-Z][A-Za-z'\-]+\.?)){1,3})"
    r"(?:,?\s*(?:Ed\.?\s?D\.?|Ph\.?\s?D\.?|Jr\.?|Sr\.?|II|III|CPA|Esq\.?))?$")

# A WARRANT ARTICLE IS NOT A SIGNATURE. Town-meeting articles carry `(Submitted by the
# Town Manager)`, and counting those put the denominator at 730 when the real number of
# report signatures is far smaller.
WARRANT = re.compile(r'recommends? approval|VOTED|PASS(?:ED)? OVER|Article \d|'
                     r'town meeting|Selectmen and Finance', re.I)
NOISE = re.compile(r'https?://|@|\bpage\b|^\W*$|^\d', re.I)
# Words that make a line a TITLE rather than a name.
TITLEISH = re.compile(r'chair|director|superintendent|chief|manager|clerk|treasurer|'
                      r'collector|agent|commissioner|inspector|coordinator|principal|'
                      r'president|secretary|officer|administrator|librarian|warden|'
                      r'member|trustee|committee|board|commission|assessor|supervisor',
                      re.I)


# A HEADING NAMES A BODY, and that is a positive test rather than a list of the ways a
# line can fail to be one. Rejecting anything that LOOKED like a person still filed five
# signatures under `Nadine Lorenzen` and five under `Heather R. Lemieux`, because a
# capitalised line has more shapes than a name-matcher covers. A department heading
# contains a word that names an organisation; a signature block never does.
BODY = re.compile(r'\b(department|commission|committee|board|office|school|library|'
                  r'council|authority|trust|fund|service[s]?|bureau|division|district|'
                  r'town|police|fire|works|aging|health|planning|zoning|cemetery|'
                  r'conservation|assessors|clerk|treasurer|collector|veterans|parks|'
                  r'recreation|housing|historical|cultural|finance|accountant|'
                  r'technology|facilities|sewer|water|building|inspection)\b', re.I)


def _is_person(text):
    """Does this capitalised line name a person rather than a body?"""
    t = RANK.sub('', re.sub(r'\s+', ' ', text).strip().title()).strip()
    return bool(PERSON.match(t)) and not TITLEISH.search(t)


def _pages(fy):
    import extract_staffing_by_section as X
    return X.page_text(fy)


def read_year(fy, rows_idx, pages):
    """Every signature in the BOOK, attributed by page to the report it ends.

    The first version only looked inside the page ranges the contents page gives, and the
    contents reads unevenly -- 17 entries in FY2011 against 58 in FY2012 -- so it found
    151 of 730 blocks. A signature is a fact about a page; which department it belongs to
    is a separate question, and a page with no range over it should still yield the name.
    """
    owner = {}
    for r in rows_idx:
        if r['fy'] != fy or r['state'] != 'report' or not r['pdf_from']:
            continue
        for p in range(int(r['pdf_from']), int(r['pdf_to']) + 1):
            owner.setdefault(p, r['department'])
    out = []
    for _once in (0,):
        # WHERE THE CONTENTS PAGE DOES NOT REACH, THE HEADING DOES. Attribution by page
        # range left 80 of 184 signatures under `(not in the contents page)`, because the
        # contents reads unevenly. A department's report is headed by its name in capitals,
        # so the last such heading before a signature is the body that signed it -- the
        # same fallback `extract_department_staffing.py` uses, and with the same caveat:
        # a running header from another page can carry over, so the CONTENTS wins wherever
        # it has an answer.
        # A SIGNATURE BLOCK IS OFTEN SET IN CAPITALS, so the name that signs a report
        # looks exactly like the heading of the next one. `JAMES P MARINO` became the
        # heading three lines above its own signature, and the name-filter then cleared
        # it -- which is how the same 80 stayed unattributed through three different
        # fixes. So heading tracking is SUSPENDED for the few lines after a signature
        # phrase, which is precisely where the signer's own name sits.
        flat, head, hush = [], '', 0
        for p in sorted(pages):
            for ln in pages.get(p, []):
                t = re.sub(r'\s+', ' ', ln).strip()
                if SIG.search(t):
                    hush = 4
                # A NAME IN CAPITALS IS NOT A HEADING. Signature blocks are often set in
                # capitals, so `NADINE LORENZEN` and `HEATHER R. LEMIEUX` were promoted to
                # departments -- five signatures each filed under the person who signed
                # them. A heading names a BODY: it survives only if it is not a person.
                # HEADINGS CARRY ACROSS PAGES, and the BODY word test was the mistake:
                # a report's heading sits pages before the signature that ends it, and
                # rejecting `SPECIAL SERVICES` or `LUNENBURG HIGH SCHOOL` for lacking a
                # listed keyword left the tracker stale and 80 signatures unattributed.
                # Everything capitalised is a candidate; the people are removed afterwards
                # by NAME, using the names this dataset itself collected.
                if HEADING.match(t) and hush <= 0:
                    head = t.title()
                hush -= 1
                flat.append((p, t, head))
        r = None
        for i, (p, line, head) in enumerate(flat):
            if not SIG.search(line) or WARRANT.search(line):
                continue
            # The name may sit on the same line after the phrase, or on the next.
            tail = SIG.split(line)[-1].strip(' ,.:;-')
            cands = ([tail] if tail else []) + [t for _p, t, _h in flat[i + 1:i + 4]]
            person = title = ''
            for c in cands:
                c = c.strip(' ,.:;-')
                if not c or NOISE.search(c):
                    continue
                if WARRANT.search(c):
                    break
                if not person:
                    # `Sheila M. Harrity, Ed.D.` and `Kate Burnham, Superintendent`
                    head = RANK.sub('', c.split(',')[0].strip()).strip()
                    m = PERSON.match(head)
                    if m and not TITLEISH.search(head):
                        person = m.group(1)
                        rest = c[len(head):].strip(' ,')
                        if rest and TITLEISH.search(rest):
                            title = rest
                        continue
                elif not title and TITLEISH.search(c):
                    title = c
                    break
            if person:
                out.append(dict(fy=fy,
                                # ATTRIBUTION IS THE CONTENTS PAGE OR NOTHING. Three
                                # attempts to fall back on the nearest capitalised
                                # heading each filed some signatures under the person who
                                # signed them, because a capitalised line has more shapes
                                # than a name-matcher enumerates. A signature is a solid
                                # fact -- this person, this title, this page -- and which
                                # body it belongs to is a SEPARATE question that the
                                # town's own contents page answers where it reaches.
                                # Guessing the rest would put names in the org chart under
                                # departments that do not exist.
                                department=owner.get(p) or head or '',
                                person=person.strip(),
                                title=title.strip()[:70], page=p,
                                as_printed=line[:120]))
    return out


def build():
    idx = list(csv.DictReader(open(INDEX, encoding='utf-8')))
    out = []
    for fy in sorted({r['fy'] for r in idx}):
        out += read_year(fy, idx, _pages(fy))
    # A POST-CONDITION, NOT A GUESS AT THE INPUT. Three attempts to stop a person's name
    # becoming a department -- reject name-shaped headings, require a body word, strip
    # ranks -- each removed some and left others, because a capitalised line has more
    # shapes than any matcher enumerates. So the OUTPUT is checked instead: if the thing
    # we are about to call a department is a person, it is not one.
    # A DEPARTMENT THAT IS SOMEBODY'S NAME IS NOT A DEPARTMENT, and the test for that is
    # this dataset's own `person` column rather than another guess at what names look
    # like. Three regex attempts each filed some signatures under the person who signed
    # them; the list of people is right here, already extracted.
    people = {r['person'].strip().lower() for r in out if r['person']}
    for r in out:
        d = r['department'].strip()
        if not d or d.lower() in people or d.lower() == r['person'].strip().lower():
            r['department'] = ''
    seen, uniq = set(), []
    for r in out:
        k = (r['fy'], r['department'], r['person'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    uniq.sort(key=lambda r: (r['fy'], r['department'].lower(), r['person']))
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    if a.check:
        old = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        if len(old) != len(rows) or any(
                any(str(r[k]) != o[k] for k in FIELDS) for r, o in zip(rows, old)):
            print('STALE %s' % OUT)
            return 1
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    per = collections.Counter(r['fy'] for r in rows)
    print('%d signatures across %d years, %d departments'
          % (len(rows), len(per), len({r['department'] for r in rows})))
    for fy in sorted(per):
        print('  FY%s  %3d' % (fy, per[fy]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
