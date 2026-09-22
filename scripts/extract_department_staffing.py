#!/usr/bin/env python3
"""What each town department says about its own staffing, in its own words.

    python3 scripts/extract_department_staffing.py
    python3 scripts/extract_department_staffing.py --check

Writes `sources/data/department-staffing.csv`.

WHY THIS EXISTS. TJ, on being told a budget line falling is not a cut: *"'cuts' are
service reductions, which we have to find in ways other than budget information. The
immediate one is staffing."* The wage list stopped naming departments after FY2016 and
there is no roster for most departments -- so I told him the town does not print who works
there. He asked *"and you are SURE..."* and he was right to: I had searched our own
extraction plan, found no roster rows, and reported OUR silence as the town's. Rule 13c,
for the second time in one day.

DEPARTMENTS DESCRIBE THEIR OWN STAFFING IN THE PROSE OF THEIR REPORTS, every year. No
heading names it, which is exactly why it went unread -- the same reason fifteen years of
out-of-district placement counts sat unread in the same documents until somebody looked.

WHAT IS CAPTURED AND WHAT IS PARSED ARE DIFFERENT THINGS, deliberately. The sentence is
stored VERBATIM, because that is the source and a reader must be able to check it. Counts
are parsed only where the form is unambiguous, into their own columns, and where it is not
the row still exists with `parsed=no`. A statement that cannot be counted is evidence that
the town said something; it is not a number.

AND THE FORMS DO NOT AGREE WITH EACH OTHER. The Fire Department gives a count and a RANGE
(`10 Career and 30-35 On Call/Per Diem`). The DPW gives an establishment, post by post
(`one Director, one Executive Assistant (shared with the Facilities Department), one
Highway Superintendent, 5 Heavy Equipment Operators...`). The Building Department gives a
list of names. Those are three different quantities and they may not be summed into a town
total -- which is why `measure` says which kind each row is, and nothing aggregates across
kinds.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
OUT = os.path.join(ROOT, 'sources', 'data', 'department-staffing.csv')

FIELDS = ['fy', 'page', 'department', 'measure', 'career', 'on_call_low', 'on_call_high',
          'positions', 'parsed', 'statement']

# The regional school district reprints the same paragraphs about itself in every town's
# annual report -- leadership "comprised of", students "comprised of", career and technical
# education. It is not Lunenburg's staffing and it matched every pattern here.
NOT_OURS = re.compile(r'montachusett|monty\s*tech|regional\s+vocational|sending\s+communit'
                      r'|easement|fringe benefits', re.I)

# TENSE, PLURALS AND THE WORDS A DEPARTMENT HEAD ACTUALLY CHOSE. The first version matched
# `staff consists of` and missed `The Council on Aging staff CONSISTED of; Doreen C. Noble,
# Director, Susan Doherty, Admin. Asst.` -- a named staff list, in the past tense, which is
# how somebody writing a report about a year that has finished would naturally put it.
#
# TJ: *"for all departments where you dont have counts over years, we need to check the
# annual reports to see if they are there and we missed them"*, and then *"i expect every
# department on town-personell to show up with data here"*. This is that check: the phrase
# list is now what people write rather than what one department happened to write.
NUMS = 'one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve'

TRIGGER = re.compile(
    r'staff (?:consists?|consisted|is comprised|was comprised|includes?|included)'
    r'|(?:department|office|commission|council|board) (?:consists?|consisted'
    r'|is comprised|was comprised|is staffed|employs?|employed)'
    r'|consists? of the following|consisted of the following'
    r'|(?:our|the) staff (?:is|are|was|were)'
    r'|staffing (?:as of|is now|is currently|level[s]? (?:is|are|remain))'
    r'|\bcareer\s+(?:and|firefighters)'
    r'|is (?:staffed|served) by'
    r'|staff of (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+'
    r'(?:individual|person|people|employee|member)'
    # `...new to their jobs in 2019-we only employ ten total-and the staff is happier
    # than ever` -- the Library's headcount, in an aside, inside a sentence about
    # turnover. No heading, no table, no list. Rule 13c: the pattern not matching was a
    # fact about this reader, and the Library was reported as publishing nothing.
    r'|\bemploys?\s+(?:a total of\s+)?(?:\d+|%s)\b' % NUMS, re.I)

HEADING = re.compile(r"^[A-Z][A-Z &/'.\-]{6,}$")

# A BOARD IS NOT A PAYROLL, and widening the trigger swept both in. `The Historical
# Commission consists of five appointed VOLUNTEERS` and `The Zoning Board consists of five
# member and three associate MEMBERS` are board memberships -- real, and already counted
# from the officials listing on the board-composition report. `The Council on Aging staff
# CONSISTED of; Doreen C. Noble, Director, Susan Doherty, Admin. Asst.` is a payroll.
#
# Read together they would put volunteers into a headcount of people the town employs,
# which is the distinction this whole pair of reports is built on. So each statement is
# classified and the two never mix.
BOARDISH = re.compile(r'\bvolunteers?\b|\bappointed members\b|\bassociate members\b'
                      r'|\bmembers are\b|\bfollowing members\b|\bmember and\b'
                      r'|\bserve (?:a|three|five)\b|\bterm[s]?\b', re.I)
STAFFISH = re.compile(r'\bstaff\b|\bemploy|\bpersonnel\b|\bfull[- ]?time\b'
                      r'|\bpart[- ]?time\b|\bdirector\b|\bassistant\b|\bclerk\b'
                      r'|\bfirefighter|\bofficer', re.I)

WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
         'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12}

# `10 Career and 30-35 On Call/Per Diem Firefighters`, and `eight Career and 40-45 On Call`
# -- the count is sometimes a numeral and sometimes a word, in the same sentence shape.
FIRE = re.compile(r'(\d+|%s)\s+career\s+and\s+(\d+)\s*[-–]\s*(\d+)\s+on[\s-]?call'
                  % '|'.join(WORDS), re.I)

# `one Director`, `5 Heavy Equipment Operators`, `two Seasonal Cemetery Laborers`.
# Where a named list begins, and the job titles inside it.
# `staff is` AND `staff was` ARE NOT LIST OPENERS, and admitting them cost two false
# rosters: `The staff is also using Teach Like a Champion by Doug Lemov` counted a book and
# its author as two employees of the elementary school, and `The staff is eagerly awaiting
# a new era at the Lunenburg Public Library with a new Director, Muir Haman` counted a
# library sentence as the IT department's payroll. Only `consists of` / `consisted of`
# actually introduces a list.
# `The department consists of Casey Burlingame who is the Building Commissioner and Zoning
# Enforcement Officer. Lisa Normandin is the Administrative Assistant...` -- the Building
# Department's FY2022 roster, its THIRD layout in three years: a colon-list in FY2020,
# flowing `X serves as the Y` prose in FY2021, and this. Same four people every time.
NAMED_LIST = re.compile(r'staff (?:consists? of|consisted of|includes?|included)\s*[;:]?\s*'
                        r'|(?:department|office|division) (?:consists? of|consisted of)'
                        r'\s*[;:]?\s*'
                        r'|consists? of the following personnel\s*[;:]?\s*'
                        r'|consisted of the following personnel\s*[;:]?\s*', re.I)

# A COUNT WITH NO NUMERAL AND NO NAME. The Assessing office writes `the Assessor's office
# staff consists of a full time Principal Assessor and a full time Assessors Clerk` and
# `a full time Principal Assessor, a 19-hour Data Collector and a 32-hour Assessing
# Administrative Assistant` -- an establishment, posted one article at a time, with the
# hours attached. Nothing in it is a digit a post-counter would find, and nothing in it is
# a person's name, so it fell through both readings.
ARTICLE_POST = re.compile(r'\b(?:a|an|one)\s+(?:(?:full|part)[\s-]time\s+|\d+-hour\s+)?'
                          r'([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,3})')

# `A facilities staff of two individuals remains on-call 24 hours a day` -- Facilities
# states its headcount as a word, in a sentence about being on call, in three years.
# A ROTA IS NOT A PAYROLL. `A facilities staff of one individual remains ON-CALL 24 hours
# a day 365 days per year` says how many people are reachable at three in the morning, not
# how many work there -- and the paragraph it sits in is a section of the DPW'S OWN REPORT
# (`a list of buildings and properties maintained by the DPW`), not a department's return.
# Published as a headcount it made Facilities the smallest employer in town at one person,
# against a Facilities & Grounds budget of about a million dollars. Rule 7: a proxy is
# never the thing.
NOT_A_HEADCOUNT = re.compile(r'remains?\s+on[\s-]?call|on[\s-]?call\s+24\s+hours', re.I)

HEADCOUNT = re.compile(r'staff of (\d+|%(n)s)\s+(?:individual|person|people|employee|member)'
                       r'|employs?\s+(?:a total of\s+)?(\d+|%(n)s)\s+'
                       r'(?:total|people|persons?|staff|individuals?|employees?)'
                       % dict(n=NUMS), re.I)
ROLE = re.compile(
    r'\b(Director|Assistant Director|Administrative Assistant|Admin\.? Assts?\.?'
    r'|Admin\.? Asst\.?|Outreach(?: Coordinator| Worker)?|Coordinator|Clerk'
    r'|Custodian|Van Driver|Driver|Nurse|Secretary|Bookkeeper|Receptionist'
    r'|Program Coordinator|Activities Coordinator|Chef|Cook|Aide)\b', re.I)

# WHERE THE STAFF LIST STOPS. The Council on Aging follows its roster with `Board Members
# during this period were Peter Lincoln, Chairperson, ...` in the same paragraph, and
# every one of those volunteers would otherwise be counted as an employee.
LIST_END = re.compile(r'\bBoard\s+(?:Members|of Directors)\b|\bMembers of the Board\b'
                      r'|\bBoard members\b|\bvolunteers\b', re.I)

# A PERSON IS TWO CAPITALISED WORDS THAT ARE NOT JOB WORDS. `Susan Doherty` is a person;
# `Meal Site`, `Administrative Assistant` and `MART Van` are not, and each of them matches
# the same shape. So the job vocabulary is excluded by hand rather than guessed at.
JOB_WORD = set('''director assistant assistants administrative admin asst assts outreach
coordinator clerk custodian van driver drivers nurse secretary bookkeeper receptionist
program activities chef cook aide meal site manager transportation mart senior center
council aging department town office worker workers supervisor foreman laborer laborers
operator operators inspector agent treasurer collector accountant technician librarian
principal superintendent chief captain lieutenant sergeant officer commissioner
building electrical plumbing gas zoning data collector assessor assessors assessing
lead public health library pages page facilities grounds highway cemetery veterans
conservation planning treasurer collectors animal control wiring sealer harbor
part full time hour hours board town's'''.split())
NAME = re.compile(r"\b([A-Z][a-z]{1,})(?:\s+[A-Z]\.?)?(?:\s+\([A-Z][a-z]+\))?"
                  r"\s+((?:Mc|Mac|O')?[A-Z][a-zA-Z'-]{1,})\b")


def named_people(tail):
    """The people named in a staff sentence, deduplicated, board members excluded."""
    cut = LIST_END.search(tail)
    if cut:
        tail = tail[:cut.start()]
    # `Electrical Inspector-Jack Biery`. THE HYPHEN IS THE SEPARATOR, not part of a name,
    # and leaving it joined read `Officer-Casey` as one token -- so the Building
    # Department's four-person list came back as one person. A hyphen is only opened up
    # where the word in front of it is a JOB word, because `Smith-Jones` has the identical
    # shape and is somebody's surname.
    tail = re.sub(r'\b([A-Za-z]+)-(?=[A-Z])',
                  lambda m: m.group(1) + ' ' if m.group(1).lower() in JOB_WORD
                  else m.group(0), tail)
    people = []
    for first, last in NAME.findall(tail):
        if first.lower() in JOB_WORD or last.lower() in JOB_WORD:
            continue
        who = '%s %s' % (first, last)
        if who not in people:
            people.append(who)
    return people

POST = re.compile(r'\b(\d+|%s)\s+([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,3})'
                  % '|'.join(WORDS))


# THE HEADING ABOVE A SENTENCE IS NOT ALWAYS ITS DEPARTMENT. The tracker takes the last
# all-capitals line, and on a page whose running header is `PROPERTY` or a mid-page label
# reads `FIRE RESCUE`, the Fire Department's own staffing sentence gets filed under it. The
# sentence names itself, so where it does, it wins.
SELF_NAMED = [(re.compile(r'\bfire department\b', re.I), 'Fire Department'),
              (re.compile(r'\bpolice department\b', re.I), 'Police Department'),
              (re.compile(r'\bbuilding department\b', re.I), 'Building Department'),
              (re.compile(r'department of public works|\bDPW\b', re.I),
               'Department of Public Works'),
              (re.compile(r'council on aging', re.I), 'Council on Aging'),
              # The Library's one headcount sat under a CEMETERY running header, which is
              # rule 13c's other half: the heading above a sentence is not always its
              # department, and a page's own words beat a header carried from elsewhere.
              (re.compile(r'\bat (?:the|your) library\b|\blibrary staff\b'
                          r'|Lunenburg Public Library', re.I), 'Library'),
              (re.compile(r'Information Technology Department|\bIT Department\b'
                          r'|The Technology Team|current IT staff', re.I),
               'Information Technology')]


SMALL = {'of', 'on', 'and', 'the', 'for', 'to', 'in', 'at'}


def name_of(head, statement):
    for pat, name in SELF_NAMED:
        if pat.search(statement):
            return name
    if not head:
        return '(unheaded)'
    # `.title()` gives `Department Of Public Works` and `Board Of Assessors`, which is not
    # how the town writes either of them and not how they are written anywhere else here.
    words = head.title().split()
    return ' '.join(w if i == 0 or w.lower() not in SMALL else w.lower()
                    for i, w in enumerate(words))


def count(tok):
    return int(tok) if tok.isdigit() else WORDS.get(tok.lower(), 0)


def statements(path):
    """Every staffing sentence on the town's own pages, with the heading above it."""
    page, head = None, ''
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        t = re.sub(r'^\s*\d+\|', '', line).rstrip()
        s = t.strip()
        if HEADING.match(s):
            head = s
        # MATCH AGAINST A SINGLE-SPACED COPY, YIELD THE ORIGINAL. These pages are set in
        # two columns and a line box spans both, so FY2022 prints `The FY22 Council on
        # Aging staff` and `consisted of Susan Doherty,` on ONE line with the column gutter
        # between them. Every trigger here writes a literal space, so a gutter is enough to
        # hide a whole roster -- and it hid that one, which is why FY2022 read as a year
        # the senior centre published no staff.
        flat = re.sub(r'\s+', ' ', s)
        if not s or NOT_OURS.search(flat) or not TRIGGER.search(flat):
            continue
        yield page, head, s


def join_wrapped(path):
    """The sentence and the line after it, because these paragraphs wrap mid-clause.

    `The staff consists of one Director, one Executive Assistant (shared with the Facili`
    ends there and continues `ties Department), one Highway Superintendent, 5 Heavy
    Equipment Operators...` on the next line. Reading only the matched line gets the first
    two posts and loses the department.
    """
    lines, page = [], None
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        lines.append((page, re.sub(r'^\s*\d+\|', '', line).strip()))
    return lines


# A PERIOD AFTER AN ABBREVIATION IS NOT THE END OF A SENTENCE. The FY2023 Council on Aging
# roster was cut at `Sandra Ricci, Asst.` and published five people against nine the year
# before and ten the year after -- a truncation that would have read as a cut of half the
# senior centre's staff. Sentence-boundary disambiguation: a title, an initial or a street
# abbreviation keeps the sentence open.
ABBREV_END = re.compile(r'(?:\b(?:[Aa]sst|[Aa]dmin|[Aa]ssoc|[Dd]ept|Sr|Jr|Mr|Mrs|Ms|Dr'
                        r'|St|Ave|Rd|Inc|Co|Ltd|[Aa]pprox|[Ee]st|etc|vs|No)\.'
                        r'|\b[A-Z]\.)$')


# A ROSTER LAID OUT AS BIOGRAPHIES. Information Technology prints `Following is an
# overview of our current IT staff:` (FY2016-FY2018) or `The Technology Team` (FY2020) and
# then one BLOCK per person -- a `Name - Role` line followed by bulleted career notes:
#
#     Steve Malandrinos - Information Technology Director
#     * Hired in December, 2012
#     Previously an engineer at Cisco Systems, IT Director for the Town of Belchertown, MA
#     Daniel Nadareski - Network Administrator
#     ...
#
# Nothing in the sentence machinery can reach it: the roster runs fifteen to eighteen
# lines and the sentence reader takes four. TJ guessed IT was outsourced, which would have
# been a good reason for it to publish nothing -- and the page names every member of the
# team in four separate years. Rule 13c again: the absence was ours.
# FY2017 WRAPS THE OPENER: the line ends `Following is an overview of our current IT` and
# `staff:` begins the next one, so a pattern anchored on the word `staff` missed a year
# whose roster is identical to the three around it.
TEAM_OPENER = re.compile(r'overview of our current\b'
                         r'|^The Technology Team$|our staff (?:is|are) as follows', re.I)
BIO_ENTRY = re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+(?:Mc|Mac|O')?[A-Z][a-zA-Z'-]+)"
                       r"\s+[-\u2013\u2014]\s+([A-Z][A-Za-z/ ]{3,60})$")
BIO_WINDOW = 24


def bio_rosters(lines, idx):
    """Every `Name - Role` block roster on the page, as (page, opener, names)."""
    out = []
    for i, (page, t) in enumerate(lines):
        flat = re.sub(r'\s+', ' ', t).strip()
        if not TEAM_OPENER.search(flat):
            continue
        names = []
        for j in range(i + 1, min(i + 1 + BIO_WINDOW, len(lines))):
            nxt = re.sub(r'\s+', ' ', lines[j][1]).strip()
            if HEADING.match(nxt):
                break
            m = BIO_ENTRY.match(nxt)
            if m and not re.search(r'\d', m.group(2)):
                who = m.group(1)
                if who not in names:
                    names.append('%s, %s' % (who, m.group(2).strip()))
        if len(names) >= 2:
            out.append((page, flat, names))
    return out


def read_year(fy):
    path = os.path.join(PAGES, 'FY%s.ocr.txt' % fy)
    if not os.path.exists(path):
        return []
    lines = join_wrapped(path)
    idx = {(p, t): i for i, (p, t) in enumerate(lines)}
    out = []
    for page, head, s in statements(path):
        i = idx.get((page, s))
        # Take up to four following lines, stopping at a blank or a new heading: the
        # establishment sentences run to three lines in some years.
        whole = s
        if i is not None:
            for j in range(i + 1, min(i + 5, len(lines))):
                nxt = lines[j][1]
                if not nxt or HEADING.match(nxt):
                    break
                whole += ' ' + nxt
                if nxt.endswith('.') and not ABBREV_END.search(nxt):
                    break
        whole = re.sub(r'(\w)-\s+(\w)', r'\1\2', whole)   # rejoin words split at the margin
        whole = re.sub(r'\s+', ' ', whole).strip()

        # Classify BEFORE parsing: a board membership never becomes a staff count.
        boardish = bool(BOARDISH.search(whole)) and not re.search(
            r'\bstaff\b|\bemploy|\bpersonnel\b', whole, re.I)
        f = FIRE.search(whole)
        row = dict(fy=fy, page=page, department=name_of(head, whole),
                   measure='board membership, not staff' if boardish else '',
                   career='', on_call_low='', on_call_high='',
                   positions='', parsed='no', statement=whole[:600])
        hc = HEADCOUNT.search(whole)
        if boardish:
            pass
        elif hc and NOT_A_HEADCOUNT.search(whole):
            row.update(measure='on-call availability, not a headcount')
        elif hc:
            row.update(measure='a stated headcount', parsed='yes',
                       career=count(hc.group(1) or hc.group(2)))
        elif f:
            row.update(measure='career and on-call firefighters', parsed='yes',
                       career=count(f.group(1)), on_call_low=int(f.group(2)),
                       on_call_high=int(f.group(3)))
        # THE OPENER AND THE FORM ARE SEPARATE QUESTIONS. This branch used to require the
        # words `staff consists of`, so FY2025's DPW establishment -- the same fourteen
        # posts as FY2023 and FY2024 -- was skipped because that year's department head
        # wrote `Our staff INCLUDES one Director, one Executive Assistant...`, and it fell
        # through to the name reader, which found `Heavy Equipment` and `Sewer Business`
        # and published the DPW as two people. Any list opener; the numbered posts decide.
        elif NAMED_LIST.search(whole):
            posts = [(count(a), b.strip()) for a, b in POST.findall(whole)]
            posts = [(n, w) for n, w in posts if n and len(w) > 3]
            # TWO POSTS MAKE AN ESTABLISHMENT. ONE IS USUALLY THE YEAR. `The FY 19 Council
            # on Aging staff consisted of Susan Doherty, Director; ...` matched `19
            # Council` and published the senior centre as nineteen posts of Council --
            # a roster of nine people, read as an establishment, by the fiscal year in its
            # own first three words.
            if len(posts) > 1:
                row.update(measure='establishment, post by post', parsed='yes',
                           positions='; '.join('%d %s' % (n, w) for n, w in posts),
                           career=sum(n for n, _w in posts))
            # AND IF IT IS NOT AN ESTABLISHMENT IT IS STILL A LIST. Making these separate
            # branches of one elif chain meant a sentence that opened a list and failed the
            # establishment test was never read at all -- FY2019's Council on Aging went
            # from nineteen posts to nothing, when it is nine people either way.
            #
            # A NAMED STAFF LIST IS A HEADCOUNT. The Council on Aging writes `staff
            # consisted of; Doreen C. Noble, Director, Susan Doherty, Admin. Asst. &
            # Transportation, Faith A. Anderson, Outreach...` in every report, which is a
            # roster in a sentence -- and it went uncounted for a day because the trigger
            # wanted the present tense.
            if row['parsed'] != 'yes':
                # COUNTED BY NAME, NOT BY ROLE -- and the first version of this counted roles
                # and was wrong by more than half. FY2024 names ten people and matched five
                # role words, because `Elsa Watson and Ann Penney, Meal Site Assistants` is two
                # people under one title and `Jim McGuigan, David Gallagher, & Kimberly Moore,
                # MART Van Drivers` is three. A roster is a count of people; counting the job
                # words beside them is the same error as reading seven officers off a police
                # page that runs to twenty-five.
                tail = whole[NAMED_LIST.search(whole).end():]
                people = named_people(tail)
                # TWO NAMES ARE A LIST. ONE IS A MENTION. `Board Of Assessors ... Clerk` and
                # `Information Technology ... Director` name one person in passing, and
                # publishing that as the department's staff would say the assessing office is
                # one person.
                if len(people) >= 2:
                    row.update(measure='a named staff list', parsed='yes',
                               positions='; '.join(people),
                               career=len(people))
                else:
                    # NO NAMES MEANS IT MAY STILL BE A LIST OF POSTS. Two or more posts, each
                    # introduced by its own article, is an establishment written out longhand.
                    posts = [w.strip() for w in ARTICLE_POST.findall(tail)
                             if len(w.strip()) > 3]
                    if len(posts) >= 2:
                        row.update(measure='an establishment, one post at a time',
                                   parsed='yes', positions='; '.join(posts),
                                   career=len(posts))
        out.append(row)
    for page, opener, names in bio_rosters(lines, idx):
        out.append(dict(fy=fy, page=page,
                        department=name_of('', opener) if name_of('', opener) != '(unheaded)'
                        else 'Information Technology',
                        measure='a named roster, one biography per person',
                        career=len(names), on_call_low='', on_call_high='',
                        positions='; '.join(names), parsed='yes',
                        statement=('%s %s' % (opener, ' | '.join(names)))[:600]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = []
    for f in sorted(glob.glob(os.path.join(PAGES, 'FY*.ocr.txt'))):
        rows += read_year(re.search(r'FY(\d{4})', f).group(1))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
    by = collections.Counter(r['department'] for r in rows)
    print('%d staffing statements across %d years; %d parsed'
          % (len(rows), len({r['fy'] for r in rows}),
             sum(1 for r in rows if r['parsed'] == 'yes')))
    for d, n in by.most_common(10):
        print('  %-34s %d' % (d[:34], n))
    if a.check:
        cur = open(OUT, encoding='utf-8', newline='').read() if os.path.exists(OUT) else ''
        if cur != buf.getvalue():
            print('  STALE — run: python3 scripts/extract_department_staffing.py')
            return 1
        print('  department-staffing.csv is current')
        return 0
    open(OUT, 'w', encoding='utf-8', newline='').write(buf.getvalue())
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
