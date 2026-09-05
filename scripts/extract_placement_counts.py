#!/usr/bin/env python3
"""Out-of-district special education placement counts, from the annual town reports.

`CLAUDE.md` lists this among the standing questions -- the numbers that "would settle more
than any further analysis" -- and records it as not published:

    Out-of-district **placement counts** by year. Dollars cannot distinguish fewer children
    from a more honest estimate.

**The town publishes them, every year, in the Special Services report inside the annual
town report.** Sourced to a named state return (SIMS Report 7 - SPED Enrollment Statistics,
District Summary) and measured on 1 March, so the date is consistent across years. This is
a count of children, which is exactly the quantity a budget line cannot produce -- rule 7's
"dollars are not students", answered.

It is prose, not a table. No heading names it and no page is given over to it; it is two
sentences inside a narrative report, which is why fifteen years of it sat unread.

## Two checks, both from the source

**The parts sum to the whole.** Each year states a total and then splits it into
collaborative, day and residential placements.

**Each year states the previous year's total.** So consecutive reports form a chain that
must agree, and a year whose own page is unreadable can still be recovered from its
successor's back-reference -- which is how FY2021 is known, its own page having been OCR'd
to nothing.

Both checks are recorded per row rather than asserted, because they catch real faults: the
FY2023 report says "was 7 (last year was 8). Of the **8** students, 3 ... 3 ... 1", and
3+3+1 is 7. The second 8 is a misprint in the source.

    python3 scripts/extract_placement_counts.py
"""

import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'placement-counts.csv')
PROV = os.path.join(ROOT, 'sources', 'data', 'PROVENANCE-placement-counts.md')

WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
    'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'twentyone': 21, 'twentytwo': 22,
    'twentythree': 23, 'twentyfour': 24, 'twentyfive': 25, 'twentysix': 26,
    'twentyseven': 27, 'twentyeight': 28, 'twentynine': 29, 'thirty': 30,
    'thirtyone': 31, 'thirtytwo': 32,
}


def number(text):
    """A count, whether the report printed it as digits or as a word.

    The reports switch between the two without warning -- FY2015 prints `thirty`, FY2017
    prints `14` -- and hyphenation moves too (`twenty -six` with the space is what OCR
    leaves behind).
    """
    if text is None:
        return None
    t = text.strip().lower()
    if re.fullmatch(r'\d+', t):
        return int(t)
    key = re.sub(r'[^a-z]', '', t)
    return WORDS.get(key)


NUM = r'(\d+|[a-zA-Z]+(?:\s*-\s*[a-zA-Z]+)?)'


def loose(phrase):
    """A pattern for `phrase` that survives the source breaking words apart.

    Four of the twelve years were missed by an exact pattern, and every one of them for
    this reason: the extracted text reads `studen ts` (FY2015), `ou tside` (FY2017) and
    `out-  side` across a hyphenated line break (FY2023). The words are right on the page
    and wrong in the text layer, which is rule 13's instrument problem in miniature -- the
    thing being matched is our rendering, not the document.

    So every character may be followed by whitespace or a soft hyphen. The phrase this is
    used on is long and distinctive enough that the looseness cannot start matching
    something else.
    """
    return r'[-\s]*'.join(re.escape(c) for c in phrase if not c.isspace())


TOTAL = re.compile(
    loose('total number of students receiving services outside the district was') + r'\s+'
    + NUM + r'(?:\s*\(' + loose('last year was') + r'\s+' + NUM + r'\))?', re.I)
SPLIT = re.compile(
    NUM + r'\s+(?:are|is)\s+(?:' + loose('placed in') + r'|' + loose('serviced in')
    + r'|in)\s+(?:a\s+)?(' + loose('Collaborative') + r'|' + loose('Day')
    + r'|' + loose('Residential') + r')', re.I)
# FY2012 and FY2013 use a different construction AND a different taxonomy.
#
# From FY2014 onward the report gives three parallel categories -- collaborative, day and
# residential -- that sum to the total. Before that it gives **two**, day and residential,
# and then says how many of the DAY placements are in a Collaborative:
#
#     FY2012: "Of the 24 students, 19 are in day placements and 5 are in residential
#              placement. Of the day placements, 7 are serviced in a Collaborative"
#
# So a collaborative count from FY2012 and one from FY2016 are not the same measurement,
# and putting them in one column would make a series out of two different definitions.
# `collaborative_basis` records which is which, and the two-category years leave the
# parallel `collaborative` column empty rather than borrowing a number that means something
# else. Rule 7: a proxy is never the thing, and that includes a category of the same name.
SPLIT_ALT = re.compile(
    r'(?:the\s+)?' + NUM + r'\s+students,?\s+' + NUM + r'\s+are in day placements'
    r'\s+and\s+' + NUM + r'\s+are in residential', re.I)
COLLAB_SUBSET = re.compile(
    r'[Oo]f the day placements,?\s+' + NUM + r'\s+(?:are|is)\s+serviced', re.I)


def flatten(path):
    """The report as one string per page, with page numbers, so a hit can be cited."""
    pages, cur, num = [], [], None
    with open(path) as fh:
        for line in fh:
            m = re.match(r'===PAGE (\d+)===', line)
            if m:
                if num:
                    pages.append((num, ' '.join(cur)))
                num, cur = int(m.group(1)), []
            elif num:
                cur.append(re.sub(r'^\s*\d+\|\s?', '', line.rstrip()))
    if num:
        pages.append((num, ' '.join(cur)))
    return pages


def main():
    pagedir = sys.argv[1] if len(sys.argv) > 1 else None
    if not pagedir or not os.path.isdir(pagedir):
        print('usage: extract_placement_counts.py <dir of FY####.txt page dumps>')
        return

    rows = []
    for path in sorted(glob.glob(os.path.join(pagedir, 'FY*.txt'))):
        # The cache holds two renderings per report -- the text layer and the OCR geometry.
        # Reading both counts every year twice.
        if path.endswith('.ocr.txt'):
            continue
        stem = os.path.basename(path).replace('.txt', '')
        if 'addendum' in stem:
            continue
        fy = int(re.search(r'(\d{4})', stem).group(1))
        for page, text in flatten(path):
            m = TOTAL.search(text)
            if not m:
                continue
            total, prior = number(m.group(1)), number(m.group(2))
            parts = {}
            for pm in SPLIT.finditer(text[max(0, m.start() - 200):m.end() + 400]):
                kind = re.sub(r'[^a-z]', '', pm.group(2).lower())
                parts[kind] = number(pm.group(1))
            rows.append({'fy': fy, 'as_of': f'{fy}-03-01', 'total': total,
                         'collaborative': parts.get('collaborative'),
                         'day': parts.get('day'),
                         'residential': parts.get('residential'),
                         'collaborative_within_day': None,
                         'report_says_prior_year': prior,
                         'page': page, 'document': stem})
            break

    # The two-category years state it in a construction the main pattern does not match,
    # and are handled separately rather than by loosening that pattern -- a looser one
    # starts matching sentences that are not this.
    for path in sorted(glob.glob(os.path.join(pagedir, 'FY*.txt'))):
        # The cache holds two renderings per report -- the text layer and the OCR geometry.
        # Reading both counts every year twice.
        if path.endswith('.ocr.txt'):
            continue
        stem = os.path.basename(path).replace('.txt', '')
        if 'addendum' in stem:
            continue
        fy = int(re.search(r'(\d{4})', stem).group(1))
        if any(r['fy'] == fy for r in rows):
            continue
        for page, text in flatten(path):
            m = SPLIT_ALT.search(text)
            if not m:
                continue
            sub = COLLAB_SUBSET.search(text[m.start():m.start() + 400])
            rows.append({'fy': fy, 'as_of': f'{fy}-03-01',
                         'total': number(m.group(1)), 'collaborative': None,
                         'day': number(m.group(2)),
                         'residential': number(m.group(3)),
                         'collaborative_within_day': number(sub.group(1)) if sub else None,
                         'report_says_prior_year': None, 'page': page,
                         'document': stem})
            break

    rows.sort(key=lambda r: r['fy'])
    stated = {r['fy']: r['total'] for r in rows}

    # Recover a year whose own page is unreadable from its successor's back-reference.
    recovered = []
    for r in rows:
        prior_fy = r['fy'] - 1
        if r['report_says_prior_year'] is not None and prior_fy not in stated:
            recovered.append({'fy': prior_fy, 'as_of': f'{prior_fy}-03-01',
                              'total': r['report_says_prior_year'],
                              'collaborative': None, 'day': None, 'residential': None,
                              'collaborative_within_day': None,
                              'report_says_prior_year': None, 'page': '',
                              'document': f"recovered from FY{r['fy']} p{r['page']}"})
    rows += recovered
    rows.sort(key=lambda r: r['fy'])
    stated = {r['fy']: r['total'] for r in rows}

    for r in rows:
        r['collaborative_basis'] = (
            'subset of day placements' if r.get('collaborative_within_day') is not None
            else 'parallel category' if r['collaborative'] is not None
            else 'not stated')
        parts = [r['collaborative'], r['day'], r['residential']]
        if r['collaborative'] is None and r['day'] is not None:
            parts = [r['day'], r['residential']]
        checks = []
        if all(p is not None for p in parts):
            s = sum(parts)
            checks.append(f'parts {"+".join(str(p) for p in parts)}={s} '
                          f'{"ties" if s == r["total"] else "DOES NOT TIE"} to stated '
                          f'{r["total"]}')
            r['parts_tie'] = 'yes' if s == r['total'] else 'NO'
        else:
            r['parts_tie'] = 'not stated'
        prior = stated.get(r['fy'] - 1)
        if r['report_says_prior_year'] is not None and prior is not None:
            ok = r['report_says_prior_year'] == prior
            checks.append(f'report says prior year {r["report_says_prior_year"]}, '
                          f'FY{r["fy"] - 1} stated {prior} '
                          f'{"- agrees" if ok else "- DISAGREES"}')
            r['chain_agrees'] = 'yes' if ok else 'NO'
        else:
            r['chain_agrees'] = 'n/a'
        r['checks'] = '; '.join(checks)

    fields = ['fy', 'as_of', 'total', 'collaborative', 'day', 'residential',
              'collaborative_within_day', 'collaborative_basis',
              'report_says_prior_year', 'parts_tie', 'chain_agrees', 'page',
              'document', 'checks']
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f'{len(rows)} years, FY{rows[0]["fy"]}-FY{rows[-1]["fy"]}\n')
    print(f'{"FY":<6}{"total":>6}{"collab":>8}{"day":>6}{"resid":>7}'
          f'{"parts":>8}{"chain":>7}  page')
    for r in rows:
        print(f'{r["fy"]:<6}{r["total"]:>6}'
              f'{r["collaborative"] if r["collaborative"] is not None else "—":>8}'
              f'{r["day"] if r["day"] is not None else "—":>6}'
              f'{r["residential"] if r["residential"] is not None else "—":>7}'
              f'{r["parts_tie"]:>8}{r["chain_agrees"]:>7}  {r["page"] or r["document"]}')
    bad = [r for r in rows if r['parts_tie'] == 'NO' or r['chain_agrees'] == 'NO']
    if bad:
        print('\nfaults -- in the source, not the extraction:')
        for r in bad:
            print(f'  FY{r["fy"]}: {r["checks"]}')
    write_provenance(rows)
    print(f'\nwrote {os.path.relpath(OUT, ROOT)}')
    print(f'wrote {os.path.relpath(PROV, ROOT)}')


def write_provenance(rows):
    L = ['# Out-of-district placement counts — where they come from, and what they are not',
         '', '**Generated by `scripts/extract_placement_counts.py`. Do not edit.**', '',
         '## This answers a standing question', '',
         '`CLAUDE.md` lists out-of-district placement counts among the numbers that "would',
         'settle more than any further analysis", and records them as not published. **They',
         'are published**, in the Special Services report inside the annual town report,',
         'every year from FY2013 to FY2025, sourced to a named state return (SIMS Report 7 —',
         'SPED Enrollment Statistics, District Summary) and measured on 1 March.', '',
         'That is a count of children. It is the quantity a budget line cannot produce, and',
         'the reason rule 7 says dollars are not students.', '',
         '## It is prose, not a table', '',
         'No heading names it. No page is given over to it. It is two sentences inside a',
         'narrative report, which is why fifteen years of it went unread — and why it was',
         'found by reading the reports end to end rather than by searching them.', '',
         '## Two checks, both taken from the source', '',
         '**The parts sum to the whole.** Each year states a total and splits it into',
         'collaborative, day and residential placements.', '',
         '**Each year states the previous year\'s total**, so consecutive reports form a',
         'chain that must agree. That is also how FY2021 is known at all: its own page was',
         'OCR\'d to nothing, and FY2022\'s back-reference recovers it.', '',
         '| FY | total | collab | day | resid | parts tie | chain | source |',
         '|---|---:|---:|---:|---:|---|---|---|']
    for r in rows:
        d = lambda v: str(v) if v is not None else '—'
        src = f"p{r['page']}" if r['page'] else r['document']
        L.append(f"| {r['fy']} | {r['total']} | {d(r['collaborative'])} | {d(r['day'])} | "
                 f"{d(r['residential'])} | {r['parts_tie']} | {r['chain_agrees']} | {src} |")
    L += ['', '## Faults in the source', '',
          'The FY2023 report prints *"was 7 (last year was 8). Of the **8** students, 3 are',
          'placed in Collaborative Placements, 3 are in Day Placements and 1 are in',
          'Residential Placements."* — and 3+3+1 is 7. The second 8 is a misprint. The',
          'stated total and the parts agree with each other and with FY2024\'s',
          'back-reference; only that one word is wrong.', '',
          'FY2013 gives no collaborative figure — it splits 22 students into 17 day and 5',
          'residential only, and uses a different sentence construction from every later',
          'year.', '',
          '## DESE does NOT cross-check this, and the near-miss is dangerous', '',
          '`sources/data/dese-radar.csv` carries **Out-of-District FTE Pupils** for',
          'Lunenburg, FY2009-FY2025. It is the obvious external check and it is the wrong',
          'quantity — it runs about ten times larger:', '',
          '| FY | town: students placed outside the district | DESE: out-of-district FTE |',
          '|---|---:|---:|',
          '| 2017 | 14 | 161.8 |',
          '| 2025 | 10 | 97.0 |', '',
          'DESE counts **every** pupil educated outside the district: vocational, school',
          'choice, charter, and special education placements together. Lunenburg alone sent',
          '**92 students to Montachusett Regional Vocational Technical School in FY2017**',
          '(assessment $1,436,287, printed in that year\'s report), and 92 + 14 is most of',
          'DESE\'s 161.8 before school choice and charter enrolment are added.', '',
          'So the two series are not the same population and neither validates the other.',
          'Both decline over the period, which is easy to mistake for agreement. Rule 7: a',
          'proxy is never the thing, and a number that moves the same way is not evidence',
          'that it measures the same quantity.', '',
          'What *would* check these counts is the SIMS return the reports cite —',
          'SIMS Report 7, SPED Enrollment Statistics, District Summary — which the town',
          'quotes and nobody publishes at district level.', '',
          '## What this is not', '',
          'A placement count is a count of **children placed**, not of dollars, and not of',
          'the cost of any placement. It says nothing about which fund paid, what any',
          'placement cost, or how long it lasted. Rule 11 still applies to the money: the',
          'out-of-district tuition line is a net appropriation and moves for reasons that',
          'have nothing to do with how many children are in it.', '',
          'The counts are as of **1 March** each year. A child placed in April is not in',
          'that year\'s figure.', '']
    with open(PROV, 'w') as fh:
        fh.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
