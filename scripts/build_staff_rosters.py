#!/usr/bin/env python3
"""School staff rosters, year by year, as a comparable series.

The town prints a faculty/staff roster for each school in its annual report, and has for
at least ten years. That is a decade of who was in post, by school -- and it is the only
published thing in this project that touches the standing question of whether budgeted
positions were **filled**.

Reads the per-page JSON produced by reading each dumped roster page, checks it, and writes:

    sources/data/staff-roster-entries.csv   one row per person per year
    sources/data/staff-roster-counts.csv    the aggregate: fy, school, position, count
    sources/data/staff-position-map.csv     every raw title seen and what it mapped to
    sources/data/PROVENANCE-staff-rosters.md

**Names are kept.** The town publishes them annually and they are public. They also make
the aggregate better rather than worse: a name that persists across years distinguishes a
post that was renamed from a post that turned over, and a genuine vacancy from a title the
report stopped printing. The aggregate is the goal; the names are what make it checkable.

## The check, and why it is a different one

A roster prints no total. There is nothing to reconcile against, so the reconciliation that
guards the receipts extraction is simply not available here.

What is available is **line accounting**: every non-blank line on the page must be claimed,
either as an entry or as a heading, and anything left over is reported. A page where 40 of
60 lines became entries and 20 vanished is not a roster with 40 staff -- it is a roster
that was half read, and without this check those two look identical.

So the denominator is printed on every run, per page: lines on the page, lines claimed,
lines unaccounted for.

## What a count is, and is not

Rule 7 applies with force. **A name on a roster is not a full-time equivalent.** The
rosters carry no FTE, so a 0.4 music teacher and a full-timer are one row each. They carry
no funding source, so nothing here says whether a post was paid by the town or by a grant
-- which is the load-bearing question this project keeps running into. And they are a point
in time, undated within the year.

A count of roster lines is a count of names the town printed. That is a real quantity and
it is not staffing.

    python3 scripts/build_staff_rosters.py [--pages <dir>]
"""

import argparse
import collections
import csv
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
ENTRIES = os.path.join(DATA, 'staff-roster-entries.csv')
COUNTS = os.path.join(DATA, 'staff-roster-counts.csv')
MAPFILE = os.path.join(DATA, 'staff-position-map.csv')
PROV = os.path.join(DATA, 'PROVENANCE-staff-rosters.md')

# The standardised positions. Comparing years is the whole point, and the titles do not
# compare themselves: `Admin Secty`, `Adm. Assistant`, `Administrative Assistant` and
# `Secretary` are four spellings of one post across four years.
#
# Order matters -- the first pattern that matches wins -- because `Special Education
# Teacher` must be tested before `Teacher`, and `Assistant Principal` before `Principal`.
POSITIONS = [
    ('Assistant Principal',      r'ASSIST(ANT)?\.?\s*PRINCIPAL|ASST\.?\s*PRINCIPAL'),
    ('Principal',                r'\bPRINCIPAL\b'),
    ('Superintendent',           r'SUPERINTENDENT'),
    ('Director',                 r'\bDIRECTOR\b|\bDIR\.'),
    ('Department Head',          r'DEPT\.?\s*HEAD|DEPARTMENT HEAD|\bDH\b'),
    ('Administrative Staff',     r'SECRETARY|SECTY|ADM(IN)?\.?\s*(ASSIST|SECTY|SEC)|'
                                 r'OFFICE CLERK|BOOKKEEPER|REGISTRAR'),
    ('Nurse',                    r'\bNURSE\b'),
    ('School Psychologist',      r'PSYCHOLOGIST'),
    ('Guidance / Adjustment Counselor',
                                 r'GUIDANCE|COUNSEL|ADJUSTMENT'),
    ('Speech / OT / PT',         r'SPEECH|LANGUAGE PATHOL|\bSLP\b|OCCUPATIONAL THERAP|'
                                 r'PHYSICAL THERAP|\bOT\b|\bPT\b'),
    ('Behaviour / BCBA',         r'\bBCBA\b|BEHAVIOU?R'),
    ('Paraprofessional',         r'\bPARA\b|PARAPROF|\bAIDE\b|TUTOR'),
    ('Special Education Teacher',
                                 r'SPECIAL ED|\bSPED\b|RESOURCE ROOM|LEARNING CENTER'),
    ('Specialist Teacher',       r'\bART\b|\bMUSIC\b|PHYS(ICAL)? ED|\bP\.?E\.?\b|'
                                 r'LIBRAR|MEDIA|TECHNOLOG|WORLD LANGUAGE|SPANISH|FRENCH|'
                                 r'\bBAND\b|CHORUS|HEALTH ED'),
    ('Classroom Teacher',        r'TEACHER|\bGR(ADE)?\.?\s*\d|\b\d[A-F]\b|KINDERGARTEN|'
                                 r'PRE-?SCHOOL|\bMATH\b|SCIENCE|LANGUAGE ARTS|'
                                 r'SOCIAL STUDIES|ENGLISH|HISTORY'),
    ('Coach / Athletics',        r'\bCOACH\b|ATHLETIC'),
    ('Custodial / Facilities',   r'CUSTOD|MAINTENANCE|FACILIT'),
    ('Food Service',             r'CAFETERIA|FOOD SERV|\bLUNCH\b|KITCHEN'),
]


# Not a role. The Turkey Hill grade blocks print a TEAM COLOUR in the column where every
# other roster prints a title, so `role_raw` for those rows is White, Blue or Red. Reading
# them as job titles would invent three positions that do not exist; dropping them silently
# would lose that the page says nothing about what those teachers do.
NOT_A_ROLE = re.compile(r'^(WHITE|BLUE|RED|GREEN|YELLOW|GOLD|SILVER|\*|[0-9]{1,4})$', re.I)


def canonical(raw, heading=None):
    """The standardised position for a printed title, or None if nothing matches.

    None is deliberate. Bucketing an unrecognised title into `Other` makes the aggregate
    look complete while quietly losing the thing that would have told you the taxonomy is
    wrong; every unmapped title is printed instead, and the count of them is the measure
    of how much the standardisation is guessing.
    """
    t = re.sub(r'\s+', ' ', (raw or '').strip().upper())
    if NOT_A_ROLE.match(t):
        t = ''
    if not t:
        # **Where no role is printed, the section heading IS the role.** Whole columns of
        # these rosters -- most of Turkey Hill, the grade lists -- print names only, with
        # the position carried entirely by the heading above them: `Grade 3`, `Guidance`,
        # `Special Education`. 1,537 of 3,815 entries are like that, so refusing the
        # fallback leaves 40% of the archive unclassified for want of a convention the
        # documents themselves use.
        #
        # `position_from` records which it was, so a count built on headings can be told
        # apart from one built on printed titles.
        t = re.sub(r'\s+', ' ', (heading or '').strip().upper())
    if not t:
        return None
    for name, pat in POSITIONS:
        if re.search(pat, t):
            return name
    return None


def source_lines(pages_dir, json_name):
    """The numbered lines of the .txt the JSON was read from, as {line_no: text}."""
    txt = os.path.join(pages_dir, json_name.replace('.json', '.txt'))
    out = {}
    if not os.path.exists(txt):
        return out
    with open(txt) as fh:
        for raw in fh:
            m = re.match(r'\s*(\d+)\|\s?(.*)$', raw.rstrip('\n'))
            if m:
                out[int(m.group(1))] = m.group(2)
    return out


def tokens(text):
    """Word tokens worth checking. Short and numeric ones are dropped: they collide across
    a page and would pass anything."""
    return [t for t in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text or '')]


def attribution_errors(page, lines):
    """Entries whose name or role does not appear on the line they were attributed to.

    This is the second check, and it is the one that catches the error the first cannot.
    Line accounting proves every line was *claimed*; it cannot prove a name was claimed by
    the right line. A column read one row out of step accounts for every line perfectly and
    attributes every person to their neighbour -- which is what happened, and what this
    found.

    Compared as token sets rather than strings, because a surname-first source
    (`Santry, Timothy`) is legitimately stored reordered.

    A wrapped role is a real exception: a title printed across two lines cannot appear
    whole on either. Those are reported separately rather than counted as errors, because
    an exception list that swallows the failures is no check at all.
    """
    hard, wrapped, inherited = [], [], []
    for e in page.get('entries', []):
        n = e.get('line')
        if not n or n not in lines:
            continue
        here = lines[n].lower()
        near = ' '.join(lines.get(k, '') for k in (n - 1, n, n + 1)).lower()
        # NAME is the hard check; ROLE is not.
        #
        # A role is legitimately inherited from a column heading printed above the row --
        # whole columns of these rosters carry no individual title, only a section heading
        # governing them. Flagging that as a misattribution buries the real failure in 90
        # false positives.
        #
        # A NAME, though, must be on the line it is attributed to. If it is not, the row
        # has been paired with its neighbour, and that is the one error line accounting
        # cannot catch: a column read one row out of step consumes every line perfectly and
        # still gets every person wrong.
        for field in ('name',):
            for tok in tokens(e.get(field)):
                if tok.lower() in here:
                    continue
                (wrapped if tok.lower() in near else hard).append(
                    {'line': n, 'field': field, 'token': tok,
                     'entry': f"{e.get('name')} / {e.get('role_raw')}",
                     'printed': lines[n].strip()[:80]})
    # Roles are checked separately and reported, not failed.
    for e in page.get('entries', []):
        n = e.get('line')
        if not n or n not in lines:
            continue
        here = lines[n].lower()
        for tok in tokens(e.get('role_raw')):
            if tok.lower() not in here:
                inherited.append({'line': n, 'field': 'role_raw', 'token': tok,
                                  'entry': f"{e.get('name')} / {e.get('role_raw')}",
                                  'printed': lines[n].strip()[:70]})
                break
    return hard, wrapped, inherited


def load_pages(pages_dir):
    out = []
    for path in sorted(glob.glob(os.path.join(pages_dir, '*.json'))):
        with open(path) as fh:
            try:
                out.append((os.path.basename(path), json.load(fh)))
            except json.JSONDecodeError as e:
                print(f'  {os.path.basename(path)}: unreadable JSON -- {e}')
    return out


def line_accounting(page):
    """Lines on the page, lines claimed, and what was left over.

    A roster has no printed total, so this is the only check there is.
    """
    total = int(page.get('lines_on_page') or 0)
    claimed = set()
    for e in page.get('entries', []):
        if e.get('line'):
            claimed.add(int(e['line']))
    for n in page.get('headings', []) or []:
        claimed.add(int(n))
    for n in page.get('ignored', []) or []:
        claimed.add(int(n))
    missing = sorted(set(range(1, total + 1)) - claimed) if total else []
    return total, len(claimed), missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', default=os.path.join(DATA, 'rosters'))
    args = ap.parse_args()

    pages = load_pages(args.pages)
    if not pages:
        print(f'No page JSON in {os.path.relpath(args.pages, ROOT)} -- '
              f'run dump_roster_pages.py and read each page first.')
        return

    entries, ledger, unmapped = [], [], collections.Counter()
    all_hard, all_wrapped, all_inherited = [], [], []
    for fname, page in pages:
        total, claimed, missing = line_accounting(page)
        lines = source_lines(args.pages, fname)
        hard, wrapped, inherited = attribution_errors(page, lines)
        all_hard += [dict(h, file=fname) for h in hard]
        all_wrapped += [dict(w, file=fname) for w in wrapped]
        all_inherited += [dict(i, file=fname) for i in inherited]
        fy, school = page.get('fy'), page.get('school')
        for e in page.get('entries', []):
            printed = (e.get('role_raw') or '').strip()
            usable = printed and not NOT_A_ROLE.match(printed.upper())
            pos = canonical(e.get('role_raw'), e.get('grade_or_dept'))
            if pos is None:
                unmapped[re.sub(r'\s+', ' ', (e.get('role_raw') or '').strip())] += 1
            entries.append({
                'fy': fy, 'school': school, 'page': page.get('page'),
                'name': (e.get('name') or '').strip(),
                'role_raw': (e.get('role_raw') or '').strip(),
                'position': pos or '',
                'position_from': ('printed role' if usable and pos
                                  else 'section heading' if pos
                                  else ''),
                'grade_or_dept': (e.get('grade_or_dept') or '').strip(),
                'line': e.get('line'), 'document': page.get('document'),
            })
        ledger.append({'file': fname, 'fy': fy, 'school': school,
                       'page': page.get('page'), 'document': page.get('document'),
                       'lines': total, 'claimed': claimed,
                       'unaccounted': len(missing),
                       'misattributed': len(hard),
                       'wrapped': len(wrapped),
                       'missing_lines': ' '.join(str(m) for m in missing[:20]),
                       'entries': len(page.get('entries', []))})

    with open(ENTRIES, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'school', 'page', 'name', 'role_raw',
                                           'position', 'position_from', 'grade_or_dept',
                                           'line', 'document'])
        w.writeheader()
        w.writerows(sorted(entries, key=lambda r: (str(r['fy']), str(r['school']),
                                                   r['line'] or 0)))

    agg = collections.Counter()
    for e in entries:
        agg[(e['fy'], e['school'], e['position'] or '(unmapped)')] += 1
    with open(COUNTS, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['fy', 'school', 'position', 'count'])
        for (fy, school, pos), n in sorted(agg.items(),
                                           key=lambda kv: (str(kv[0][0]), str(kv[0][1]),
                                                           kv[0][2])):
            w.writerow([fy, school, pos, n])

    with open(MAPFILE, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['role_as_printed', 'position', 'times_seen'])
        seen = collections.Counter((e['role_raw'], e['position']) for e in entries)
        for (raw, pos), n in sorted(seen.items()):
            w.writerow([raw, pos, n])

    bad = [r for r in ledger if r['unaccounted']]
    print(f'{len(pages)} roster pages read, {len(entries)} entries')
    print(f'{sum(r["lines"] for r in ledger)} lines on those pages, '
          f'{sum(r["claimed"] for r in ledger)} accounted for, '
          f'{sum(r["unaccounted"] for r in ledger)} not')
    if bad:
        print('\npages with unaccounted lines -- these are NOT complete rosters:')
        for r in bad:
            print(f'  {r["file"]}: {r["unaccounted"]} of {r["lines"]} lines '
                  f'(first few: {r["missing_lines"]})')
    if all_hard:
        by_file = collections.Counter(h['file'] for h in all_hard)
        print(f'\n{len(all_hard)} entries attributed to a line that does not contain '
              f'them -- a column read out of step accounts for every line perfectly and '
              f'still pairs every person with their neighbour:')
        for f, n in by_file.most_common():
            print(f'  {f}: {n}')
        for h in all_hard[:12]:
            print(f"    {h['file']} line {h['line']}: {h['field']} token "
                  f"{h['token']!r} not on that line")
            print(f"      entry:   {h['entry']}")
            print(f"      printed: {h['printed']}")
    if all_inherited:
        print(f'\n{len(all_inherited)} entries whose ROLE is not printed on their own '
              f'line -- a column heading applied to the rows it governs, which is how '
              f'these rosters work where a column prints no individual titles. Not an '
              f'error; listed so it is a decision rather than an assumption.')
    if all_wrapped:
        print(f'\n{len(all_wrapped)} tokens found on an adjacent line -- titles printed '
              f'across a line break, not errors, but listed so the distinction is made '
              f'by evidence rather than assumed.')
    if unmapped:
        print(f'\n{len(unmapped)} titles the taxonomy does not recognise '
              f'({sum(unmapped.values())} entries). They are stored with an empty '
              f'position, never bucketed as Other:')
        for raw, n in unmapped.most_common(25):
            print(f'  {n:>4}  {raw[:70]}')

    write_provenance(ledger, entries, agg, unmapped, all_hard, all_wrapped)
    for p in (ENTRIES, COUNTS, MAPFILE, PROV):
        print(f'wrote {os.path.relpath(p, ROOT)}')


def write_provenance(ledger, entries, agg, unmapped, hard=(), wrapped=()):
    years = sorted({str(r['fy']) for r in ledger if r['fy']})
    L = ['# School staff rosters — what was read, and what a count means', '',
         '**Generated by `scripts/build_staff_rosters.py`. Do not edit.**', '',
         '## A count of roster lines is not a staffing level', '',
         'Rule 7. The rosters carry **no FTE**, so a 0.4 music teacher and a full-timer are',
         'one row each. They carry **no funding source**, so nothing here says whether a',
         'post was paid by the town or by a grant — the question this project keeps',
         'running into. They are **a point in time**, undated within the year.', '',
         'A count here is a count of names the town printed. That is a real quantity and it',
         'is not staffing.', '',
         '## There is no total to check against', '',
         'A roster prints no total, so the reconciliation that guards every other extract in',
         'this project is unavailable. The check is **line accounting**: every non-blank',
         'line on the page is claimed as an entry or a heading, and the leftovers are',
         'counted. A page where a third of the lines vanished looks exactly like a smaller',
         'school unless somebody counts.', '']
    tot = sum(r['lines'] for r in ledger)
    acc = sum(r['claimed'] for r in ledger)
    L.append(f'**{acc} of {tot} lines accounted for** across {len(ledger)} pages, '
             f'{len(entries)} entries, {len(years)} years.')
    L.append('')
    L.append('| page | FY | school | lines | claimed | unaccounted | entries | misattributed |')
    L.append('|---|---|---|---:|---:|---:|---:|---:|')
    for r in sorted(ledger, key=lambda r: (str(r['fy']), str(r['school']))):
        L.append(f"| {r['file']} | {r['fy']} | {r['school']} | {r['lines']} | "
                 f"{r['claimed']} | {r['unaccounted']} | {r['entries']} | "
                 f"{r.get('misattributed', 0)} |")
    L.append('')
    L.append('## The second check: is a name on the line it was attributed to')
    L.append('')
    L.append('Line accounting proves every line was **claimed**. It cannot prove a name was')
    L.append('claimed by the **right** line — a column read one row out of step accounts for')
    L.append('every line perfectly and pairs every person with their neighbour. So every')
    L.append("entry's name and role tokens are checked back against the printed line.")
    L.append('')
    L.append(f'**{len(hard)} entries fail this check.** {len(wrapped)} more have a token on')
    L.append('an adjacent line, which is a title printed across a line break rather than an')
    L.append('error — listed separately so the distinction rests on evidence.')
    L.append('')
    if hard:
        L.append('| page | line | field | token | entry | printed |')
        L.append('|---|---:|---|---|---|---|')
        for h in hard[:80]:
            L.append(f"| {h['file']} | {h['line']} | {h['field']} | `{h['token']}` | "
                     f"{h['entry']} | `{h['printed']}` |")
        L.append('')
    if unmapped:
        L.append('## Titles the taxonomy does not recognise')
        L.append('')
        L.append('Stored with an empty `position`, never bucketed as `Other` — a title that')
        L.append('silently becomes `Other` makes the aggregate look complete while hiding')
        L.append('that the taxonomy is wrong.')
        L.append('')
        L.append('| times | printed as |')
        L.append('|---:|---|')
        for raw, n in unmapped.most_common(60):
            L.append(f'| {n} | `{raw}` |')
        L.append('')
    L.append('## Two things a count here must not be read as')
    L.append('')
    L.append('**FY2024 Turkey Hill is 135 entries against a typical ~60.** The FY2024 report')
    L.append('prints TWO complete Turkey Hill rosters, on pages 107 and 108, with different')
    L.append('principals — Norman Yvon and Heidi Champagne — and different staff in many')
    L.append('posts. Nothing on either page says which year each describes. Summing them')
    L.append('doubles that school for that year.')
    L.append('')
    L.append('**Sixteen people appear on two rosters in a single year** — district-wide or')
    L.append('shared staff. That is the source, not a duplication bug. A naive dedupe')
    L.append('undercounts and a naive sum double-counts; the choice has to be made')
    L.append('deliberately and stated.')
    L.append('')
    L.append('And `monty-tech` is a seventh school value covering six administrators of the')
    L.append('regional vocational school Lunenburg SENDS students to. They are not Lunenburg')
    L.append('staff and must be excluded from any district headcount.')
    L.append('')
    L.append('## Names')
    L.append('')
    L.append('Kept. The town publishes them annually in a public document. They also make')
    L.append('the aggregate checkable: a name persisting across years separates a post that')
    L.append('was renamed from one that turned over, and a real vacancy from a title the')
    L.append('report stopped printing.')
    L.append('')
    with open(PROV, 'w') as fh:
        fh.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
