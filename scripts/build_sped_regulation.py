#!/usr/bin/env python3
"""The class-size rule for special education: 603 CMR 28.06(6) and (7), quoted.

    python3 scripts/build_sped_regulation.py
    python3 scripts/build_sped_regulation.py --check

Writes `fy28/public/data/sped-regulation.json`, which /special-education-class-size
renders.

WHY THIS PAGE EXISTS, AND WHY IT IS NOT ONE OF THE FOUR SPECIAL EDUCATION REPORTS

Residents argue about paraprofessional staffing constantly, and the rule the argument is
actually about -- eight students to one certified special educator, twelve with an aide --
was in nobody's published record for this town until the regulation was ingested. Every
other report on this site MEASURES Lunenburg. This one QUOTES A STATUTE, sets the town's
own published placement counts beside it, and stops. That is a different grain and it
gets a different page, and a different section of the index.

WHAT THIS PAGE MUST NOT DO, and it is the whole risk

**It must not compute a required number of paraprofessionals for Lunenburg.** The
regulation binds INSTRUCTIONAL GROUPS. Nothing published says how many groups Lunenburg
runs, how large each is, or how its substantially separate students are divided among
them -- and the same count of children is lawful at very different staffing levels
depending on how they are grouped. That limit is registered in `sources/data/money-gaps.csv`
as *"How many paraprofessionals Lunenburg needs, against how many it employs"*, and this
generator quotes that row BY ITS TEXT rather than restating it, so the page and the
registry cannot drift (rule 7c: the registry outranks the page).

Rule 8: this is not a compliance audit. Nothing here establishes that Lunenburg is over-
or under-staffed, and the page says so in those words.

EVERY QUOTED PHRASE IS READ OUT OF THE EXTRACTED TEXT ON EVERY RUN, and every number in
the scenario table is PARSED OUT OF THE SENTENCE THAT STATES IT rather than typed. Rule 13:
a rendering is never the thing. So `eight` in the table is the word `eight` found inside
the clause it was found in, and if DESE republishes the regulation with a different figure
this build stops rather than publishing yesterday's rule under today's citation.

THE THING THAT IS EASIEST TO GET WRONG HERE, and the reason the parser is structural.
28.06(6)(c) -- groups outside general education 60% OR LESS of the schedule -- has THREE
tiers, the third being 16 students with a certified special educator and TWO aides.
28.06(6)(d) -- substantially separate, MORE than 60% -- has TWO, and stops at 12 with one
aide. That asymmetry is the most interesting thing in the table and the easiest thing in
the world to smooth over, so the build asserts it: `two aides` occurs exactly once in the
entire regulation, and the (d) block contains no third tier.

AIDE IS NOT ESTABLISHED TO MEAN PARAPROFESSIONAL. The regulation says `aide` and never
defines it; 28.02(3) defines `certified special educator` and there is no matching
definition of the other. `paraprofessional` appears in 603 CMR 28.00 twice, both in the
staff-training clauses of 28.03(1)(a), one of which names *teachers, paraprofessionals,
and teacher assistants* as three things. DESE's staffing files and the district's budget
lines say paraprofessional. This page says they are the words two different documents use
and asserts nothing about whether they are the same job.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import conclusions as C                                              # noqa: E402
from conclusions import conclusion, emit, figure                     # noqa: E402
# The provenance, meeting-archive and manifest plumbing every report shares. Imported
# rather than copied: a second implementation of `doc()` is a second thing that can stop
# checking that a figure has a document behind it.
from build_special_education import (                                # noqa: E402
    DESE, MINUTES, ROOT, archive, coverage, doc, fail, manifest,
)

DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT = os.path.join(PUB, 'sped-regulation.json')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')

REG_KEY = 'state-dese/603cmr28-special-education-regulations.html'
REG_TEXT = 'state-dese/text/603cmr28-special-education-regulations.txt'
SIMS_KEY = 'state-dese/sims-datahandbook-current.docx'
PROG_KEY = 'state-dese/dese-sped-program-characteristics.xlsx'

LEA = '01620000'
TOWN = 'Lunenburg'

# The gap row this page is built around, quoted by the exact question it registers. If
# somebody rewords it in the registry, this build stops -- which is rule 7c's "the
# registry outranks the page" as an assertion rather than an instruction.
GAP_WHAT = ('How many paraprofessionals Lunenburg needs, against how many it employs')

# The two limits this page ADDED to the registry while it was being written, because
# rule 7c says a conclusion you cannot draw is a gap and it gets registered rather than
# living in one paragraph of one page. Both are quoted by their question, so a reword in
# the registry stops this build rather than leaving the page saying something the request
# letter no longer asks for.
GAP_ALSO = (
    'Whether an “aide” in the class-size regulation is a paraprofessional the '
    'town budgets',
    'Where 16 of Lunenburg’s students with disabilities are placed, in FY2026',
    'Whether an aide assigned to one child also counts as the aide that raises a group '
    'from eight students to twelve',
)

SEARCHED = ['class size', 'paraprofessional', 'caseload', 'substantially separate',
            '603 CMR']

# What the meeting archive was searched for and what came back is computed below. The
# QUOTES are filled from that search -- see notes/process/PERSONAS.md step 3, which is the
# step a verifier cannot do.
QUOTES = [
    dict(key='noaides', board='finance-committee', date='2026-01-12',
         kind='minutes', doc='7597',
         quote='noting that kindergarten classrooms were operating with 25 students and '
               'no aides',
         why='The nearest thing in the whole meeting archive to a Lunenburg group size '
             'said out loud beside a staff count. It is a KINDERGARTEN class \u2014 a '
             'general education classroom \u2014 and 28.06(6) governs special education '
             'instructional groupings, so this is not a figure the rule applies to. It is '
             'here because it is the shape of the argument residents are having.'),
    dict(key='noformula', board='finance-committee', date='2024-03-14',
         kind='minutes', doc='6469',
         quote='Julianna Hanscom states there is no formula. The school is aware of what '
               'students are in programs who will then go into a program next year. There '
               'hasn\u2019t been a large or small caseload, and the inclusion of teachers '
               'is between 15 to 20 students',
         why='The Director of Special Education, asked how the budget decides staffing, '
             'answering that there is no formula. That is consistent with a regulation '
             'that sets MAXIMUMS and requires judgement below them \u2014 and it is a '
             'statement about how the district budgets, not a measurement of any group.'),
    dict(key='pullout', board='finance-committee', date='2026-01-27',
         kind='minutes', doc='7619',
         quote='seven of her IEP students with significant pull-out service needs were '
               'being seen by a paraprofessional rather than a certified special '
               'education teacher',
         why='A Turkey Hill special education teacher, in public comment. The regulation '
             'draws exactly this line \u2014 28.02(3) defines the certified special '
             'educator and never defines the aide \u2014 which is why the distinction '
             'matters. THIS IS NOT EVIDENCE OF A BREACH, and the same clause is why: it '
             'says a certified special educator may "provide, design, or supervise" '
             'special education services, so a service delivered by somebody the educator '
             'supervises is contemplated by the regulation. What is established is that a '
             'teacher said this at a public meeting. What is not is how many students, '
             'which posts, or what supervision was in place; no FTE by assignment is '
             'published.'),
    dict(key='backbone', board='school-committee', date='2024-01-24',
         kind='minutes', doc='6375',
         quote='they are the backbone of special education and without them the '
               'department cannot run',
         why='A parent, in the public comment on the FY25 budget, on the proposed '
             'paraprofessional cuts. It establishes that residents argue about '
             'paraprofessional numbers. It establishes nothing about instructional '
             'groups, which is what the regulation on this page binds.'),
]


# ---------------------------------------------------------------- the regulation, read

WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
         'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12}


def count(tok):
    """A number the regulation writes as a word or as digits, as an int.

    The regulation mixes the two INSIDE ONE SENTENCE -- `eight students`, then `12
    students`, then `16 students` -- so anything reading these has to take both, and a
    token that is neither is a parse that has drifted rather than a value to guess at."""
    t = tok.strip().lower()
    if t.isdigit():
        return int(t)
    if t in WORDS:
        return WORDS[t]
    fail('%r is neither a numeral nor a number word the regulation uses. The sentence '
         'this was parsed out of has changed shape' % tok)


def regulation():
    """The extracted text, as lines, with the body's top-level clauses located by their
    own opening words rather than by a line number or by a `(6)` that repeats.

    WHY NOT THE HTML ANCHORS. DESE's page gives every clause a `<p id="(6)(d)">`, which
    looks like an address and is not one: 481 of them carry 242 distinct ids, because the
    numbering restarts in every section. `(3)` appears eleven times. A location is not an
    identity -- the shape of almost every defect in this repository.

    WHY NOT THE SECTION HEADINGS EITHER. The body prints a heading for 28.01 through
    28.06 and then for 28.08, and 28.07's clauses sit inside 28.06's range with no heading
    of their own. So a search for `(6)(b)` scoped to "the 28.06 section" can land in
    28.07. Every block below is therefore bounded by the FIRST WORDS OF THE CLAUSE ITSELF,
    which are unique in the document, and the build asserts that uniqueness."""
    path = os.path.join(ROOT, 'sources', REG_TEXT)
    if not os.path.exists(path):
        fail('%s is not here -- the whole page is a quotation of it' % REG_TEXT)
    return open(path, encoding='utf-8').read()


# THE EXTRACT OPENS WITH THE PAGE'S OWN TABLE OF CONTENTS, and a count taken over the
# whole file counts it twice. `28.09: Approval of Public or Private Day and Residential
# Special Education School Programs` is a heading, printed once in the contents and once
# over the section -- so counting the words the tier table leans on across the whole file
# reports two uses of a term the regulation used once. Every COUNT below is therefore
# taken over the body, which begins at the SECOND occurrence of the first heading.
#
# The clause extraction is unaffected: it locates each passage by its own opening words,
# which are unique in the file. This is only about counting.
BODY_STARTS = '28.01: Authority, Scope and Purpose'


def body(whole):
    """The regulation without its own table of contents."""
    first = whole.find(BODY_STARTS)
    second = whole.find(BODY_STARTS, first + 1)
    if first < 0 or second < 0:
        fail('the extracted regulation no longer carries a table of contents followed by '
             'its body, and every count on this page is taken over the body')
    return whole[second:]


def only(text, needle, what):
    """The one place `needle` occurs, or a stop. Rule 13: a quote that matches twice was
    never checked against anything."""
    n = text.count(needle)
    if n != 1:
        fail('%s occurs %d times in the regulation, not once. %r is no longer a unique '
             'handle on it' % (what, n, needle[:60]))
    return text.index(needle)


def block(text, opens, closes, what):
    """The clause running from its own opening words to the next clause's."""
    a = only(text, opens, '%s (its opening)' % what)
    b = only(text, closes, '%s (the clause after it)' % what)
    if b <= a:
        fail('%s: the clause that should follow it comes first' % what)
    return text[a:b].strip()


def subclause(blk, label, what):
    """One lettered sub-clause of a block: the labelled line plus any unlabelled lines
    that hang off it, which is how the extract renders 28.06(7)(e) and (f)."""
    lines = [l.strip() for l in blk.split('\n')]
    starts = [i for i, l in enumerate(lines) if l.startswith('(%s) ' % label)]
    if len(starts) != 1:
        fail('%s: found %d lines beginning "(%s)" where there must be exactly one'
             % (what, len(starts), label))
    i = starts[0]
    out = [lines[i]]
    for l in lines[i + 1:]:
        if not l:
            continue
        if re.match(r'^\([a-z0-9]+\)\s', l):
            break
        out.append(l)
    return ' '.join(out)


def clauses():
    """Every passage this page quotes, pulled out of the extracted text by its own words.

    Each is returned with the citation a reader can look up, so nothing downstream has to
    remember which sentence came from where."""
    t = regulation()
    six = block(t,
                '(6) Instructional grouping requirements.',
                '(7) Programs for young children.', '28.06(6)')
    seven = block(t,
                  '(7) Programs for young children.',
                  '(8) Transportation Services.', '28.06(7)')
    defs = block(t,
                 '(3) Certified special educator shall mean',
                 '(4) Consent shall mean agreement by a parent', '28.02(3)')
    train = only(t, 'The school district shall provide such staff training in methods of '
                    'collaboration among teachers, paraprofessionals, and teacher '
                    'assistants', '28.03(1)(a), the collaboration sentence')
    approved = only(t, 'Instructional groupings and student/teacher ratios shall not '
                       'exceed the class size standards set forth at',
                    '28.09(7)(e), the approved-programs cross-reference')

    out = {
        '28.06(6)': dict(cite='603 CMR 28.06(6)', text=six.split('\n')[0].strip(),
                         title='Instructional grouping requirements'),
        '28.06(6)(b)': dict(cite='603 CMR 28.06(6)(b)',
                            text=subclause(six, 'b', '28.06(6)(b)'),
                            title='The grouping must match the IEP'),
        '28.06(6)(c)': dict(cite='603 CMR 28.06(6)(c)',
                            text=subclause(six, 'c', '28.06(6)(c)'),
                            title='Outside general education 60% or less of the schedule'),
        '28.06(6)(d)': dict(cite='603 CMR 28.06(6)(d)',
                            text=subclause(six, 'd', '28.06(6)(d)'),
                            title='Substantially separate — more than 60% of the schedule'),
        '28.06(6)(e)': dict(cite='603 CMR 28.06(6)(e)',
                            text=subclause(six, 'e', '28.06(6)(e)'),
                            title='Two more students, mid-year, by decision'),
        '28.06(6)(f)': dict(cite='603 CMR 28.06(6)(f)',
                            text=subclause(six, 'f', '28.06(6)(f)'),
                            title='No more than 48 months between youngest and oldest'),
        '28.06(7)': dict(cite='603 CMR 28.06(7)',
                         text=seven.split('\n')[0].strip(),
                         title='Programs for young children'),
        '28.06(6)(g)': dict(cite='603 CMR 28.06(6)(g)',
                            text=subclause(six, 'g', '28.06(6)(g)'),
                            title='Approved programs take the substantially separate sizes'),
        '28.06(7)(e)': dict(cite='603 CMR 28.06(7)(e)',
                            text=subclause(seven, 'e', '28.06(7)(e)'),
                            title='Young children — an inclusionary setting'),
        '28.06(7)(f)': dict(cite='603 CMR 28.06(7)(f)',
                            text=subclause(seven, 'f', '28.06(7)(f)'),
                            title='Young children — a substantially separate setting'),
        '28.02(3)': dict(cite='603 CMR 28.02(3)',
                         text=defs.split('\n')[0].strip(),
                         title='What a certified special educator is'),
        '28.03(1)(a)': dict(cite='603 CMR 28.03(1)(a)',
                            text=t[train:t.index('\n', train)].strip(),
                            title='The one place paraprofessionals are named'),
        '28.09(7)(e)': dict(cite='603 CMR 28.09(7)(e)',
                            text=t[approved:t.index('\n', approved)].strip(),
                            title='Approved schools are held to the same sizes'),
    }
    # AND EVERY PASSAGE THE PAGE WILL PRINT IS FOUND AGAIN, in the whole document, with
    # whitespace collapsed -- because the sub-clause reader joins wrapped lines with a
    # space and the file separates them with a blank line. Collapsing both is the only
    # comparison that means "this string is in that document" rather than "this string
    # survived our own reflow", which is rule 13 in one line.
    flat = re.sub(r'\s+', ' ', t)
    for k, v in out.items():
        if not v['text'] or len(v['text']) < 40:
            fail('%s came back as %r, which is not a clause' % (k, v['text'][:40]))
        only(flat, re.sub(r'\s+', ' ', v['text']),
             '%s (as this page will print it)' % k)
    return t, out


# ------------------------------------------------------------------- the scenario table

# The two words the regulation uses for the one adult in charge of a group. They are NOT
# asserted to be the same qualification -- 28.06(6) says one and 28.06(7) says the other,
# and each row carries its own clause's word so a merged table cannot quietly equate them.
EDUCATOR = 'certified special educator'
TEACHER = 'teacher'

SCHOOL_AGE = 'School age'
YOUNG = 'Young children'


def tiers(cl, whole):
    """Every group-size tier the regulation sets, in BOTH age bands, in one list.

    NOTHING HERE IS TYPED. Each row's student count, its educator count, its aide count
    and the age band it applies to come out of the clause's own words, and the shape of
    each sentence is asserted -- three tiers in (c), two in (d), two integrated preschool
    cases and one substantially separate one in (7), and exactly ONE educator in every
    single row. That last assertion is the whole point of putting them in one table: the
    educator count never changes, at any age, in any setting, and what a larger group buys
    is an aide.
    """
    # THE AGE SPLIT, from the two clauses that state it rather than from memory. The
    # regulation divides at five: 28.06(6) governs eligible students "aged five and
    # older" and 28.06(7) covers children "three and four years of age". A merged table
    # has to show that split on the row, because a reader who takes a preschool maximum
    # for a school-age one has been misled by our layout rather than by the regulation.
    sa = re.search(r'eligible students (aged [a-z]+ and older)', cl['28.06(6)']['text'])
    yg = re.search(r'eligible children ([a-z]+ and [a-z]+ years of age)',
                   cl['28.06(7)']['text'])
    if not sa or not yg:
        fail('the regulation no longer states the ages each of 28.06(6) and 28.06(7) '
             'applies to in the words this reads. A merged table cannot label its bands '
             'without them')
    school_ages, young_ages = sa.group(1), yg.group(1)

    rows = []

    c = cl['28.06(6)(c)']['text']
    head = re.search(r'group size shall not exceed (.+?)\.', c)
    if not head:
        fail('28.06(6)(c) no longer states its sizes in a sentence beginning '
             '"group size shall not exceed"')
    found = re.findall(
        r'([A-Za-z0-9]+) students (?:(with a certified special educator)|'
        r'if the certified special educator is assisted by ([a-z]+) aides?)',
        head.group(1))
    if len(found) != 3:
        fail('28.06(6)(c) parsed to %d tiers, not the three it has published: %r'
             % (len(found), head.group(1)))
    for students, alone, aides in found:
        rows.append(dict(
            setting='Outside general education 60% or less of the schedule',
            short='Partly separate', cite=cl['28.06(6)(c)']['cite'],
            band=SCHOOL_AGE, ages=school_ages, role=EDUCATOR,
            separateness='partly separate', separateness_rank=1,
            condition='', students=count(students), educators=1,
            aides=0 if alone else count(aides),
            staff=('a certified special educator' if alone
                   else 'a certified special educator assisted by %s aide%s'
                        % (aides, '' if count(aides) == 1 else 's'))))

    d = cl['28.06(6)(d)']['text']
    headd = re.search(r'instructional groupings that do not exceed (.+?)\.', d)
    if not headd:
        fail('28.06(6)(d) no longer states its sizes in a sentence beginning '
             '"instructional groupings that do not exceed"')
    foundd = re.findall(
        r'([A-Za-z0-9]+) students to (one certified special educator|'
        r'a certified special educator and an aide)', headd.group(1))
    if len(foundd) != 2:
        fail('28.06(6)(d) parsed to %d tiers, not the two it has published: %r'
             % (len(foundd), headd.group(1)))
    for students, staff in foundd:
        rows.append(dict(
            setting='Substantially separate — more than 60% of the schedule',
            short='Substantially separate', cite=cl['28.06(6)(d)']['cite'],
            band=SCHOOL_AGE, ages=school_ages, role=EDUCATOR,
            separateness='substantially separate', separateness_rank=2,
            condition='', students=count(students), educators=1,
            aides=0 if staff == 'one certified special educator' else 1,
            staff=staff))

    # THE ASYMMETRY, ASSERTED. The third tier -- sixteen students with two aides -- exists
    # only for the partly separate setting. It is the single most interesting line in this
    # table and the single easiest thing to smooth over into "the rule is 8, 12, 16", so
    # the build refuses to publish if the phrase turns up anywhere else in the regulation
    # or if the substantially separate clause grows a tier.
    if whole.count('two aides') != 1:
        fail('"two aides" occurs %d times in the regulation. The claim that the third '
             'tier exists in one clause only rests on it occurring once'
             % whole.count('two aides'))
    if max(r['aides'] for r in rows if r['short'] == 'Substantially separate') != 1:
        fail('28.06(6)(d) now names a tier with more than one aide')

    # YOUNG CHILDREN, IN THE SAME TABLE, and this is a decision rather than a tidy-up.
    #
    # These sat in a section of their own headed "a different rule again", and held out
    # like that they read as an EXCEPTION. They are not: they are the same shape carried
    # into the other age band, and merging them turns the page's strongest finding from a
    # fact about one clause into a pattern holding across every age the regulation covers.
    # TJ, on the first draft: move them up into the ratios.
    #
    # WHAT MERGING MUST NOT FLATTEN. 28.06(7) says `teacher` where 28.06(6) says
    # `certified special educator`, and nothing here establishes that those are the same
    # qualification. So every row carries the word ITS OWN clause uses, in `role`, and the
    # table prints it -- the rows sit together and are not silently made identical.
    e = cl['28.06(7)(e)']['text']
    m = re.search(r'class size shall not exceed (\d+) with ([a-z]+) teacher and ([a-z]+) '
                  r'aide and no more than ([a-z]+) students with disabilities', e)
    m2 = re.search(r'students with disabilities is ([a-z]+) or ([a-z]+) then the class '
                   r'size may not exceed (\d+) students with ([a-z]+) teacher and '
                   r'([a-z]+) aide', e)
    if not m or not m2:
        fail('28.06(7)(e) no longer states the integrated preschool class sizes in the '
             'two sentences this parses')
    # WHY THERE ARE TWO INTEGRATED ROWS, which is the first thing anybody asks of a table
    # showing one citation against two different maximums. The clause makes the class size
    # depend on HOW MANY OF THE CHILDREN HAVE DISABILITIES: up to five, and the class may
    # reach 20; six or seven, and it may not exceed 15. Both conditions are read out of
    # the sentence that states them, so the table explains itself rather than looking like
    # a parsing error.
    young = [
        dict(setting='Integrated with children who do not have disabilities',
             short='Integrated preschool', cite=cl['28.06(7)(e)']['cite'],
             band=YOUNG, ages=young_ages, role=TEACHER,
             separateness='integrated', separateness_rank=0,
             condition='up to %s of the class have disabilities' % m.group(4),
             students=int(m.group(1)), educators=count(m.group(2)),
             aides=count(m.group(3)),
             staff='%s teacher and %s aide' % (m.group(2), m.group(3)),
             swd_min=None, swd_cap=count(m.group(4))),
        dict(setting='Integrated with children who do not have disabilities',
             short='Integrated preschool', cite=cl['28.06(7)(e)']['cite'],
             band=YOUNG, ages=young_ages, role=TEACHER,
             separateness='integrated', separateness_rank=0,
             condition='%s or %s of the class have disabilities'
                       % (m2.group(1), m2.group(2)),
             students=int(m2.group(3)), educators=count(m2.group(4)),
             aides=count(m2.group(5)),
             staff='%s teacher and %s aide' % (m2.group(4), m2.group(5)),
             swd_min=count(m2.group(1)), swd_cap=count(m2.group(2))),
    ]
    f = cl['28.06(7)(f)']['text']
    m3 = re.search(r'limit class sizes to ([a-z]+) students with ([a-z]+) teacher and '
                   r'([a-z]+) aide', f)
    share = re.search(r'programs in which more than (\d+)% of the children have '
                      r'disabilities', f)
    if not m3 or not share:
        fail('28.06(7)(f) no longer states the substantially separate preschool class '
             'size and the share of children that defines the setting')
    young.append(dict(
        setting='Substantially separate — serving primarily or solely children with '
                'disabilities',
        short='Substantially separate preschool', cite=cl['28.06(7)(f)']['cite'],
        band=YOUNG, ages=young_ages, role=TEACHER,
        separateness='substantially separate', separateness_rank=2,
        condition='more than %s%% of the class have disabilities' % share.group(1),
        students=count(m3.group(1)), educators=count(m3.group(2)),
        aides=count(m3.group(3)),
        staff='%s teacher and %s aide' % (m3.group(2), m3.group(3)),
        swd_min=None, swd_cap=None))
    young_share = int(share.group(1))

    # AND THE INVARIANT IS ASSERTED ACROSS BOTH BANDS, not just the school-age one. One
    # educator in every tier the regulation sets, at every age, in every setting. That is
    # the claim the merged table exists to make, and the build refuses to publish if a
    # single row stops supporting it.
    if {r['educators'] for r in rows + young} != {1}:
        fail('a tier no longer names exactly one educator. The merged table\u2019s whole '
             'claim is that the educator count never changes and only the aides scale')

    # The two provisions that move a row rather than making one.
    mid = re.search(r'increase the size of an instructional grouping by no more than '
                    r'([a-z]+) additional students', cl['28.06(6)(e)']['text'])
    age = re.search(r'shall not differ by more than (\d+) months',
                    cl['28.06(6)(f)']['text'])
    if not mid or not age:
        fail('28.06(6)(e) or (f) no longer states its own limit in the words this parses')

    return rows, young, count(mid.group(1)), int(age.group(1)), young_share


# ------------------------------------------------------ how DESE's labels are defined

# WHAT THE REGULATION NEVER SAYS, and it has to be MEASURED rather than asserted.
#
# TJ: "include 1:1s in a classroom to show that you can have many paras/aides in a
# classroom and it doesn't count against the ratio." He is right about the substance and
# the framing is the whole risk: 603 CMR 28.00 contains NO rule about one-to-one support,
# so this may not be presented as one. What it contains is a cap on STUDENTS given a
# staffing configuration, and no cap on adults anywhere.
#
# A claim that a document says nothing about something is the easiest kind to get wrong
# and the hardest to notice being wrong, so it is a search with its terms published beside
# the result -- the same discipline as printing the denominator on a minutes search. If
# DESE ever adds a clause about individual aides, this count stops being zero and the
# build says so instead of going on publishing "the regulation is silent".
SILENT_ON = ('one-to-one', 'one to one', '1:1', 'individual aide', 'individualized aide',
             'dedicated aide', 'personal care', 'number of adults')


# THE WORDS THE TIER TABLE LEANS ON, and whether the regulation defines any of them.
#
# TJ: "make sure to define the terms of aids paras etc if the definitions exist, or say
# that if they dont". The page already tells a reader that `aide` and `paraprofessional`
# are two documents' words and asserts nothing about whether they name the same job. That
# distinction is unusable without knowing what either one means -- so the terms are set
# out, and THE ABSENCES ARE THE HALF THAT MATTERS.
#
# NOTHING IN THIS LIST DECLARES WHETHER A TERM IS DEFINED. Each is looked up in 28.02 on
# every build and the answer is whatever the search returns, so a term that gains a
# definition at DESE appears here as defined without anybody editing this file, and one
# that loses it stops being quoted rather than being quoted from memory.
#
# RULE 7 GOVERNS THE SECOND COLUMN. "The regulation uses this word nine times and never
# defines it" is a FACT and it is all that is published. What the word must therefore mean
# -- that an aide is a paraprofessional, that a teacher must hold a particular licence --
# is a hypothesis, and it is not offered. Where the regulation itself points somewhere,
# that pointer is quoted; where it points nowhere, the row says so.
TERMS = [
    'Certified special educator',
    'Special education',
    'Eligible student',
    'Least restrictive environment',
    'In-district program',
    'Out-of-district program',
    'aide',
    'paraprofessional',
    'teacher',
    'teacher assistant',
    'instructional grouping',
    'substantially separate',
    'class size',
    'one-to-one',
]


def definitions(whole):
    """Every term the tier table leans on: defined here, or used and never defined.

    The definitions section is bounded by the first definition's own opening words and
    the first clause of 28.03 -- both unique in the document -- rather than by the
    heading `28.02: Definitions`, which appears twice because the page prints a table of
    contents. A location is not an identity; that is the shape of nearly every defect in
    this repository."""
    defs_block = block(whole,
                       '(1) Approved private special education school or approved '
                       'program shall mean',
                       '(1) General Responsibilities of the School District.', '28.02')
    found = {}
    for m in re.finditer(r'\((\d+)\)\s+([A-Z][^\n]*?)\s+shall (?:mean|have the meaning)'
                         r'[^\n]*', defs_block):
        found[m.group(2).strip().lower()] = dict(number=int(m.group(1)),
                                                 term=m.group(2).strip(),
                                                 text=m.group(0).strip())
    if len(found) < 15:
        fail('603 CMR 28.02 parsed to %d definitions, and it has always carried far more. '
             'The definitions section is not being read' % len(found))

    text = body(whole)
    out = []
    for term in TERMS:
        uses = len(re.findall(r'\b' + re.escape(term), text, re.I))
        hit = None
        for key, d in found.items():
            if key == term.lower() or key.startswith(term.lower() + ' ('):
                hit = d
                break
        row = dict(term=term, uses=uses, defined=bool(hit), note='')
        if hit:
            row.update(cite='603 CMR 28.02(%d)' % hit['number'], definition=hit['text'])
        else:
            row.update(cite='', definition='')
            # AND THE ABSENCE IS ASSERTED, not assumed. A term this says is undefined must
            # not turn out to be defined somewhere else in the regulation under a slightly
            # different heading -- so the whole text is searched for it being given a
            # meaning, and the build stops if one is found.
            if re.search(r'\b' + re.escape(term) + r'\b\s+shall (?:mean|have the meaning)',
                         whole, re.I):
                fail('%r is defined somewhere in the regulation and this page is about to '
                     'publish that it is not' % term)
        if uses == 0 and term.lower() not in ('one-to-one',):
            fail('%r does not appear in the regulation at all, so a page listing it as a '
                 'term the rule uses would be wrong' % term)
        out.append(row)

    # TWO NOTES THAT ARE MEASURED RATHER THAN REMEMBERED, and both are about an absence.
    #
    # `paraprofessional` is the word the town, the district's budget and DESE's staffing
    # return all use, and the regulation that decides group sizes contains it only in the
    # clauses about STAFF TRAINING. That is checkable -- every occurrence either lies
    # inside 28.03(1) or it does not -- so it is checked, and the note is written only if
    # it holds.
    train = block(whole, '(1) General Responsibilities of the School District.',
                  '(2) Administrator of Special Education.', '28.03(1)')
    for row in out:
        if row['term'] == 'paraprofessional':
            inside = len(re.findall(r'\b' + re.escape(row['term']), train, re.I))
            if inside == row['uses']:
                row['note'] = ('every occurrence is in the staff-training clauses of '
                               '603 CMR 28.03(1)(a), one of which names \u201cteachers, '
                               'paraprofessionals, and teacher assistants\u201d as three '
                               'separate things. The regulation never says what one is, '
                               'or what one may do.')
            else:
                row['note'] = ('%d of its %d occurrences are outside the staff-training '
                               'clauses' % (row['uses'] - inside, row['uses']))
        # `teacher` is undefined here too, and the only thing the regulation says about
        # what one must hold is in the section on APPROVED SCHOOLS -- which is a
        # different population from a district classroom, and the note says so rather
        # than letting the citation imply otherwise.
        if row['term'] == 'teacher' and not row['defined']:
            lic = ('(b) Teaching staff shall have teaching licensure appropriate to meet '
                   'the needs of the population served')
            if whole.count(lic) == 1:
                row['note'] = ('the only licensure requirement anywhere in the regulation '
                               'is 603 CMR 28.09(7)(b), and it governs APPROVED SPECIAL '
                               'EDUCATION SCHOOLS rather than a district classroom. '
                               'Nothing here states what a teacher in 28.06(7) must hold.')
        if row['term'] == 'aide' and not row['defined']:
            row['note'] = ('the word that decides whether a group of eight may hold '
                           'twelve, and the regulation defines neither the person nor '
                           'their duties. It names no other document for the meaning '
                           'either.')
        if row['term'] == 'one-to-one' and row['uses'] == 0:
            row['note'] = ('searched for in %d phrasings across the full text. The '
                           'regulation contains no rule about individual support at all.'
                           % len(SILENT_ON))

    if not any(r['defined'] for r in out) or not any(not r['defined'] for r in out):
        fail('the terms table has gone all one way. Its whole point is the contrast '
             'between the words 28.02 defines and the words it only uses')
    return out


# HOW MANY EXTRA AIDES THE WORKED ROOM SHOWS, and why the number is declared here.
#
# TJ's question: "If we see 12 kids in a room, with 1 teacher and 3 paras, but each para
# is a 1:1, how does that work out?" The answer is that the room complies and has more
# staff than the rule requires -- and the room is how the page says so, because the tier
# table alone only answers it for a reader who already knows the numbers are a ceiling on
# CHILDREN rather than a description of staffing.
#
# The student count and the minimum staffing in every room below are READ OFF THE
# REGULATION. This one number is not: it is the illustration's own, chosen to match the
# room TJ described, and it is declared here rather than typed into the page so that the
# payload can say which half of each room is the rule and which half is the example.
ROOM_EXTRA_IEP_AIDES = 2


def rooms(tier_rows, sub_cap, sub_aide, cite):
    """The same group size at the rule's minimum and above it, both lawful.

    THE ASSERTION THAT MAKES THIS SAFE TO PUBLISH: every room is checked back against the
    tier it claims to satisfy. A worked example that quietly stopped satisfying the rule
    it illustrates would be the worst thing on this page, so the build recomputes it
    rather than trusting the sentence beside it."""
    tiers_here = {(t['students'], t['aides']): t for t in tier_rows
                  if t['separateness'] == 'substantially separate'
                  and t['band'] == SCHOOL_AGE}
    if (sub_cap, 0) not in tiers_here or (sub_aide, 1) not in tiers_here:
        fail('the two substantially separate tiers this page works its rooms against are '
             'no longer in the regulation as parsed')

    out = [
        dict(key='minimum-no-aide', students=sub_cap, educators=1, aides=0, iep_aides=0,
             minimum=True, cite=cite,
             headline='%d children' % sub_cap,
             verdict='Complies, at the minimum the rule allows',
             why='One certified special educator and no aide. This is the largest group '
                 'the rule permits without one.'),
        dict(key='minimum-one-aide', students=sub_aide, educators=1, aides=1, iep_aides=0,
             minimum=True, cite=cite,
             headline='%d children' % sub_aide,
             verdict='Complies, at the minimum the rule allows',
             why='The aide is what raises the ceiling from %d to %d. Nothing more is '
                 'required at this group size.' % (sub_cap, sub_aide)),
        dict(key='ieps-on-top', students=sub_aide, educators=1,
             aides=1 + ROOM_EXTRA_IEP_AIDES, iep_aides=ROOM_EXTRA_IEP_AIDES,
             minimum=False, cite=cite,
             headline='%d children' % sub_aide,
             verdict='Complies, with more staff than the rule requires',
             why='The same group size, staffed three times over. The rule asks two '
                 'questions — %d students or fewer, and a certified special educator '
                 'with an aide — and both are answered. The other %d are there '
                 'because IEPs require them, not because this rule does.'
                 % (sub_aide, ROOM_EXTRA_IEP_AIDES)),
    ]
    for r in out:
        cap = sub_cap if r['aides'] == 0 else sub_aide
        if r['students'] > cap:
            fail('the worked room %r puts %d students in a group the regulation caps at '
                 '%d. A worked example that does not satisfy the rule it illustrates is '
                 'the worst thing this page could publish'
                 % (r['key'], r['students'], cap))
        if r['educators'] != 1:
            fail('the worked room %r names %d educators' % (r['key'], r['educators']))
        if r['iep_aides'] > r['aides']:
            fail('the worked room %r assigns more individual aides than it has aides'
                 % r['key'])
    return out


def silence(whole):
    """Count each term the page says the regulation does not use. Zero is the finding."""
    text = body(whole)
    hits = [dict(term=t, count=len(re.findall(re.escape(t), text, re.I)))
            for t in SILENT_ON]
    return hits, sum(h['count'] for h in hits)


def doe034():
    """DESE's own definition of each placement label, out of the SIMS data handbook.

    THIS IS THE JOIN, AND IT IS THE ONLY THING THAT MAKES THE TWO HALVES OF THE PAGE
    COMPARABLE. The regulation keys on percentage of the school schedule outside general
    education; DESE's published placement counts key on element DOE034, whose acceptable
    values are DEFINED on that same axis. Without this the counts and the rule would be
    two things printed near each other -- which is exactly what rule 7 forbids."""
    path = os.path.join(ROOT, 'sources', SIMS_KEY)
    if not os.path.exists(path):
        fail('%s is not here -- without it the mapping between DESE’s labels and the '
             'regulation’s thresholds is an assertion' % SIMS_KEY)
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')
    text = re.sub(r'<[^>]+>', '', xml.replace('</w:p>', '\n'))
    text = text.replace('—', '—')
    # THE WHOLE VALUE LIST, from the element's own segment of the handbook -- not a
    # remembered count of it. The page needs to say that DESE's published breakdown prints
    # four of these, and "nine" was typed into a draft of that sentence and was wrong:
    # there are eight placements, plus two values that mean the child is not a special
    # education student at all. A count typed beside a table is rule 2's defect exactly,
    # and this one would have shipped.
    starts = [m.start() for m in
              re.finditer(r'Special Education Placement, ages 6\s*[\u2013-]\s*21(?!\d)',
                          text)]
    if not starts:
        fail('the SIMS data handbook no longer carries the element that defines the '
             'placement labels DESE publishes')
    seg = text[starts[-1]:text.index('Notes:', starts[-1])]
    pairs = re.findall(r'\n\s*(\d{2})\s*\n\s*([^\n]+)', seg)
    values = [dict(code=c, description=t.strip()) for c, t in pairs
              if not t.strip().lower().startswith('not ')]
    if len(values) < 5 or len(values) != len({v['code'] for v in values}):
        fail('the DOE034 value list parsed to %d placements, which is not the shape of '
             'the element' % len(values))

    want = [
        ('10', 'Full Inclusion'), ('20', 'Partial Inclusion'),
        ('40', 'Substantially Separate Classroom'),
    ]
    out = []
    for code, label in want:
        m = re.search(re.escape(label) + r' — ([^\n]+?)\s*\n', text)
        if not m:
            fail('the SIMS data handbook no longer defines %r on the axis this page joins '
                 'on. The mapping between DESE’s labels and 28.06(6) is not '
                 'established without it' % label)
        out.append(dict(code=code, label=label, definition=m.group(1).strip(),
                        element='DOE034'))
    pct = [re.search(r'(\d+)%', d['definition']) for d in out]
    if not all(pct):
        fail('a DOE034 definition no longer states a percentage, which is the axis the '
             'join is made on')
    # THE AGE SPLIT, TAKEN FROM DESE'S OWN ELEMENT HEADINGS rather than typed. The
    # regulation splits at five (28.06(6)) and at three-and-four (28.06(7)); DESE splits
    # its placement reporting into two elements at a different place. Saying so requires
    # both spans, and a span typed into a sentence is exactly rule 2's defect -- so they
    # are read off the two headings that name them.
    # The handbook prints each heading more than once -- a contents entry and the element
    # itself -- so the DISTINCT spans are what matters, not how many times they occur.
    # The trailing `(?!\d)` is load-bearing: the contents entries run the heading straight
    # into a page number -- `ages 6\u201321` becomes `ages 6\u20132137` -- and without it
    # this reads a page number as part of a child's age.
    scope = re.findall(
        r'Special Education Placement, ages (\d{1,2})\s*[\u2013-]\s*(\d{1,2})(?!\d)', text)
    spans = sorted({'%s to %s' % (a, b) for a, b in scope})
    if len(spans) != 2 or not any(s.startswith('6') for s in spans):
        fail('the SIMS handbook no longer heads its two placement elements with the age '
             'span each covers; the distinct spans found were %r' % (spans,))
    return out, dict(this=[s for s in spans if s.startswith('6')][0],
                     other=[s for s in spans if not s.startswith('6')][0]), values


# --------------------------------------------------------------- Lunenburg, set beside

def placements(db):
    rows = db.execute(
        "SELECT indicator, indicator_level, measure_cnt, denominator_cnt, measure_pct "
        "FROM dese_sped_program WHERE lea=? AND geo_level='district' "
        "AND indicator_category='Placement' AND fy=(SELECT MAX(fy) FROM dese_sped_program "
        "WHERE lea=? AND indicator_category='Placement') ORDER BY measure_cnt DESC",
        (LEA, LEA)).fetchall()
    fy = db.execute(
        "SELECT MAX(fy) FROM dese_sped_program WHERE lea=? AND indicator_category="
        "'Placement'", (LEA,)).fetchone()[0]
    if not rows or fy is None:
        fail('no placement rows came back for Lunenburg. A join that matches nothing '
             'looks exactly like a district with no children in it')
    total = [r for r in rows if r[1] == 'total']
    members = [r for r in rows if r[1] == 'member']
    if len(total) != 1 or len(members) < 3:
        fail('the placement breakdown came back as %d totals and %d members, which is not '
             'the shape this page reads' % (len(total), len(members)))
    tot = int(total[0][2])
    named = sum(int(r[2]) for r in members)
    sub = [r for r in members if r[0] == 'Substantially Separate']
    if len(sub) != 1:
        fail('DESE no longer publishes a Substantially Separate row for Lunenburg, which '
             'is the row 28.06(6)(d) governs')
    # THE FOUR PRINTED CATEGORIES DO NOT PARTITION THE TOTAL, and the page says so rather
    # than letting a reader add them up. DOE034 has nine acceptable values; this breakdown
    # prints four. Measured here rather than asserted, so if DESE starts printing the rest
    # the page stops saying it.
    return dict(
        fy=int(fy), total=tot, named=named, unnamed=tot - named,
        rows=[dict(label=r[0], count=int(r[2]), pct=round(100.0 * r[2] / tot, 1))
              for r in members],
        sub=dict(label=sub[0][0], count=int(sub[0][2]),
                 pct=round(100.0 * sub[0][2] / tot, 1)))


def gap_rows():
    import csv as _csv
    with open(GAPS, encoding='utf-8') as fh:
        by_what = {r['what'].strip(): r for r in _csv.DictReader(fh)}
    out = []
    for what in (GAP_WHAT,) + GAP_ALSO:
        r = by_what.get(what)
        if not r:
            fail('money-gaps.csv no longer registers %r. Rule 7c: the registry outranks '
                 'the page, so a page whose limits are not in the registry must not '
                 'publish' % what)
        out.append(dict(side=r['side'], what=r['what'], why=r['why']))
    return out


# ------------------------------------------------------------------ what the town said

def said():
    out = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here -- a quote on this page is attributed to a document that '
                 'is not in the archive' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            fail('the quote attributed to %s %s is no longer in %s -- quote the source, '
                 'never your rendering of it' % (spec['board'], spec['date'], rel))
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'], kind=spec['kind'],
            cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_%s%s%s-%s'
                 % (spec['date'][5:7], spec['date'][8:10], spec['date'][:4], spec['doc'])))
    return out


def searched():
    a = archive()
    return [dict(term=t, documents=sum(1 for b in a['bodies']
                                       if re.search(re.escape(t), b, re.I)))
            for t in SEARCHED]


# ------------------------------------------------------------------------------ build

def build():
    if not os.path.exists(DB):
        raise SystemExit('%s is missing. Run scripts/build_db.py.' % DB)
    db = sqlite3.connect(DB)
    mf = manifest()
    whole, cl = clauses()
    main, young, midyear, age_months, young_share = tiers(cl, whole)
    codes, ages, values = doe034()
    silent, silent_total = silence(whole)
    terms = definitions(whole)
    p = placements(db)
    gaps = gap_rows()

    # ORDERED THE WAY THE CLAUSE READS, not by student count. Within a setting the rows
    # run in the order the regulation introduces them, and for the two integrated
    # preschool rows that is by HOW MANY OF THE CLASS HAVE DISABILITIES -- up to five,
    # then six or seven -- which runs the student cap DOWNWARDS, 20 then 15. Sorting
    # those two by student count printed the exception before the base case and read as
    # an error.
    for r in main + young:
        r['order'] = r['swd_cap'] if r.get('swd_cap') is not None else r['students']
    all_tiers = sorted(main + young,
                       key=lambda r: (0 if r['band'] == SCHOOL_AGE else 1,
                                      r['separateness_rank'], r['order']))
    integrated = [r for r in all_tiers if r['separateness'] == 'integrated']
    if len(integrated) == 2 and integrated[0]['students'] < integrated[1]['students']:
        fail('the two integrated preschool rows are printing the smaller class first. '
             'The clause introduces the base case (up to five children with disabilities, '
             'class of 20) before the exception, and reversing them reads as a defect')
    bands = []
    for b in (SCHOOL_AGE, YOUNG):
        rs = [r for r in all_tiers if r['band'] == b]
        if not rs:
            fail('%s came back with no tiers, and the merged table is half a table' % b)
        bands.append(dict(
            band=b, ages=rs[0]['ages'], role=rs[0]['role'], rows=len(rs),
            cites=sorted({r['cite'] for r in rs}),
            # THE SEPARATENESS PATTERN, measured per band rather than asserted once. The
            # highest ceiling the band reaches, against the ceiling of its substantially
            # separate setting. School age falls from 16 to 12; preschool from 20 to 9.
            # Same direction, and further -- which is the claim, and it is computed.
            top=max(r['students'] for r in rs),
            top_setting=max(rs, key=lambda r: r['students'])['separateness'],
            sub=max(r['students'] for r in rs
                    if r['separateness'] == 'substantially separate'),
            drop=(max(r['students'] for r in rs)
                  - max(r['students'] for r in rs
                        if r['separateness'] == 'substantially separate'))))
    if not all(b['drop'] > 0 for b in bands):
        fail('the ceiling no longer falls as the setting gets more separate in every age '
             'band, and that pattern is a published conclusion on this page')
    sa_band, yg_band = bands[0], bands[1]
    if yg_band['drop'] <= sa_band['drop']:
        fail('the preschool ceiling no longer falls FURTHER than the school-age one '
             '(%d against %d). The page publishes "the same direction and a bigger drop" '
             'and that sentence would now be wrong'
             % (yg_band['drop'], sa_band['drop']))

    sub_cap = min(r['students'] for r in main
                  if r['short'] == 'Substantially separate')
    sub_aide = max(r['students'] for r in main
                   if r['short'] == 'Substantially separate')
    worked_rooms = rooms(all_tiers, sub_cap, sub_aide, cl['28.06(6)(d)']['cite'])
    part_cap = max(r['students'] for r in main if r['short'] == 'Partly separate')
    threshold = int(re.search(r'more than (\d+)%', cl['28.06(6)(d)']['text']).group(1))
    sub_def = [c for c in codes if c['code'] == '40'][0]

    return {
        'about': 'The state rule everybody argues around, quoted: how many students may '
                 'be in one special education instructional group, and what staff that '
                 'takes. With Lunenburg’s own published placement counts beside it, '
                 'and the reason neither one gives a staffing number.',
        'grain': 'A REGULATION and a HEADCOUNT, and they are not the same quantity.',
        'fy': p['fy'],
        'clauses': cl,
        # ONE LIST, BOTH BANDS. School age first because that is where the argument in
        # this town is, then the preschool clauses -- and within each band ordered from
        # least separate to most, because the second finding on this page is what happens
        # to the ceiling as the setting gets more separate, and a table that does not run
        # in that order hides it.
        'tiers': all_tiers,
        'bands': bands,
        'young_share': young_share,
        'terms': terms,
        'silent_on': silent,
        'silent_total': silent_total,
        'rooms': worked_rooms,
        'room_extra_iep_aides': ROOM_EXTRA_IEP_AIDES,
        'midyear_extra': midyear,
        'age_months': age_months,
        'threshold_pct': threshold,
        'sub_cap': sub_cap, 'sub_aide_cap': sub_aide, 'part_cap': part_cap,
        'codes': codes,
        'code_ages': ages,
        'code_values': values,
        'placement': p,
        'gap': gaps[0],
        'gaps_also': gaps[1:],
        'sources': [
            doc(mf, REG_KEY, '(quoted, not loaded)',
                'Massachusetts Department of Elementary and Secondary Education, '
                '603 CMR 28.00',
                'The regulation itself, as DESE publishes it in one page. Every clause '
                'quoted on this page is read out of the extracted text on every build and '
                'every figure in the table is parsed from the sentence that states it, so '
                'a change at DESE stops this build rather than being republished under '
                'the old citation.'),
            doc(mf, SIMS_KEY, '(quoted, not loaded)', DESE,
                'The Student Information Management System data handbook, which defines '
                'element DOE034 — the placement label DESE counts on — as a '
                'percentage of time outside the general education classroom. This is what '
                'makes the counts and the regulation comparable at all.'),
            doc(mf, PROG_KEY, 'dese_sped_program', DESE,
                'Special education program characteristics, the source of the placement '
                'counts. Its Placement breakdown is in-district only and its four printed '
                'categories do not sum to the total it prints beside them — measured '
                'on every build rather than assumed.'),
        ],
        'said': said(),
        'searched': searched(),
        'minutes': coverage(),
        'conclusions': emit('classsize', [
            conclusion(
                id='eight-to-one',
                claim='A substantially separate group may not exceed %s students to '
                      'one certified special educator' % C.num(sub_cap),
                so_what='With an aide it is %s. The aide is what raises the ceiling; the '
                        'teacher count never changes.' % C.num(sub_aide),
                detail='603 CMR 28.06(6)(d), quoted in full below: a setting "serving '
                       'solely students with disabilities for more than 60% of the '
                       'students’ school schedule" shall have "instructional '
                       'groupings that do not exceed eight students to one certified '
                       'special educator or 12 students to a certified special educator '
                       'and an aide". These are the numbers residents argue about, and '
                       'until this regulation was added to the archive nothing in this '
                       'town’s published record set them out.',
                figures={
                    'cap': figure(sub_cap, C.num(sub_cap), 'students'),
                    'aide': figure(sub_aide, C.num(sub_aide), 'students'),
                    'threshold': figure(threshold, '%d%%' % threshold),
                },
                allow=('603 CMR 28.06(6)(d)',),
                kind='measured', bearing='sizes', figure='cap',
                basis='603 CMR 28.06(6)(d), read out of DESE’s own published text of '
                      'the regulation on every build.',
                not_shown='Anything about Lunenburg. This is the ceiling on a GROUP, and '
                          'nothing on this page says how many groups this town runs or '
                          'how large they are.',
            ),
            conclusion(
                id='no-required-number',
                claim='Nothing published lets anybody compute how many staff this rule '
                      'requires in Lunenburg',
                so_what='%s children could be four groups or seven, needing very '
                        'different staffing. Both are lawful.' % C.num(p['sub']['count']),
                detail='The regulation binds instructional groups. Lunenburg publishes a '
                       'count of children by placement label and no count of groups, no '
                       'size for any group, and no assignment of children to them. Three '
                       'further things in the regulation would defeat a ratio even with '
                       'that list: the sizes are MAXIMUMS and districts are "expected to '
                       'exercise judgment in determining appropriate group size and '
                       'supports for smaller instructional groups serving students with '
                       'complex special needs"; grouping must be "compatible with the '
                       'methods and goals stated in each student’s Individualized '
                       'Education Program", which can require one-to-one support no class '
                       'size predicts; and a group already at maximum may take two more '
                       'students mid-year by decision of the Administrator of Special '
                       'Education. This page therefore states the rule and stops, and the '
                       'limit is a registered row in money-gaps.csv rather than a '
                       'sentence only this page carries.',
                figures={
                    'sub': figure(p['sub']['count'], C.num(p['sub']['count']),
                                  'children'),
                },
                kind='measured', bearing='sizes',
                no_figure='No published figure exists. The town publishes children by '
                          'label; the rule binds groups; nobody publishes the groups.',
                basis='603 CMR 28.06(6)(b), (c) and (e); and the absence of any published '
                      'list of Lunenburg’s special education instructional groups.',
                not_shown='That Lunenburg is over-staffed or under-staffed. Nothing on '
                          'this page supports either reading, and it is not an audit.',
            ),            conclusion(
                id='one-educator-every-tier',
                claim='Every tier the rule sets names one educator — at every age, in '
                      'every setting',
                so_what='Across all %s tiers only the aides change. A bigger group never '
                        'buys a second educator.' % C.num(len(all_tiers)),
                detail='%s tiers, in two age bands: 28.06(6)(c) and (d) for students %s, '
                       '28.06(7)(e) and (f) for children %s. In every one of them the '
                       'adult in charge is singular. What changes between %s and %s, and '
                       'between %s and %s, is an aide. The build refuses to publish this '
                       'table if a single row ever names a second educator, because the '
                       'shape is the finding.'
                       % (C.num(len(all_tiers)), sa_band['ages'], yg_band['ages'],
                          C.num(sub_cap), C.num(sub_aide), C.num(sub_aide),
                          C.num(part_cap)),
                figures={
                    'tiers': figure(len(all_tiers), C.num(len(all_tiers)),
                                    'group-size tiers'),
                    'low': figure(sub_cap, C.num(sub_cap), 'students'),
                    'mid': figure(sub_aide, C.num(sub_aide), 'students'),
                    'high': figure(part_cap, C.num(part_cap), 'students'),
                },
                allow=('28.06(6)(c)', '28.06(7)(e)'),
                kind='measured', bearing='sizes', figure='tiers',
                basis='603 CMR 28.06(6)(c) and (d) and 28.06(7)(e) and (f), parsed tier '
                      'by tier out of the sentences that state them.',
                not_shown='That the two bands name the same qualification. 28.06(6) says '
                          '"certified special educator" and 28.06(7) says "teacher", and '
                          'nothing here establishes those are the same thing — the '
                          'table prints each clause’s own word. Nor what an aide is: '
                          'the regulation never defines it, while DESE’s staffing '
                          'files and the district’s budget lines say '
                          '"paraprofessional".',
            ),
            conclusion(
                id='ceiling-falls-with-separateness',
                claim='The more separate the setting, the lower the ceiling — in both '
                      'age bands',
                so_what='School age falls %s to %s. Preschool falls %s to %s — same '
                        'direction, bigger drop.'
                        % (C.num(sa_band['top']), C.num(sa_band['sub']),
                           C.num(yg_band['top']), C.num(yg_band['sub'])),
                lede='This is the opposite of what most people assume, and it holds at '
                     'every age the regulation covers.',
                detail='28.06(6)(c) governs groups outside general education %d%% of the '
                       'schedule or less and runs to "16 students if the certified '
                       'special educator is assisted by two aides"; 28.06(6)(d), above '
                       'that threshold, names two tiers and stops at 12. The phrase "two '
                       'aides" occurs exactly once in the whole of 603 CMR 28.00, which '
                       'this build asserts on every run. The preschool clauses run the '
                       'same way and further: an integrated class may reach 20 under '
                       '28.06(7)(e), a substantially separate one is limited to 9 under '
                       '28.06(7)(f). The build refuses to publish if either band stops '
                       'falling, or if preschool stops falling further than school age.'
                       % threshold,
                figures={
                    'high': figure(sa_band['top'], C.num(sa_band['top']), 'students'),
                    'mid': figure(sa_band['sub'], C.num(sa_band['sub']), 'students'),
                    'ytop': figure(yg_band['top'], C.num(yg_band['top']), 'students'),
                    'ysub': figure(yg_band['sub'], C.num(yg_band['sub']), 'students'),
                    'threshold': figure(threshold, '%d%%' % threshold),
                },
                allow=('603 CMR 28.00', '28.06(6)(c)', '28.06(6)(d)', '28.06(7)(e)',
                       '28.06(7)(f)'),
                kind='measured', bearing='sizes', figure='ytop',
                basis='All four class-size clauses, parsed; and a count of the phrase '
                      '"two aides" across the full regulation.',
                not_shown='Why. The regulation gives no reason for the pattern and this '
                          'page offers none — any explanation would be a hypothesis '
                          'about drafting decisions nobody here witnessed. Nor are the '
                          'two bands strictly comparable: 28.06(6) caps an instructional '
                          'GROUP and 28.06(7) caps a CLASS, and the preschool clauses '
                          'count children with and without disabilities together.',
            ),
            conclusion(
                id='caps-children-not-adults',
                claim='The rule sets the MINIMUM staffing for a group size. IEPs add on '
                      'top of it',
                so_what='%s children with one educator and %s aides is lawful. So is %s '
                        'with one aide.'
                        % (C.num(sub_aide), C.num(1 + ROOM_EXTRA_IEP_AIDES),
                           C.num(sub_aide)),
                lede='This is the most misread thing about the class-size rule, and it '
                     'runs in both directions.',
                detail='Take the room people actually ask about: %s children, one '
                       'certified special educator, and %s aides of whom %s are assigned '
                       'to individual children by their IEPs. The rule asks two questions '
                       '— are there %s students or fewer, and is there a certified '
                       'special educator with an aide — and both are answered, so '
                       'the room complies and has more staff than the rule requires. '
                       'Every tier caps CHILDREN given a staffing configuration; not one '
                       'of them limits adults. A room may also hold a speech therapist '
                       'and a behaviour specialist and the class-size rule speaks to '
                       'neither. So a room at the legal minimum and a room staffed three '
                       'times over look identical from outside, which is why "we have a '
                       'lot of paras" and "our groups are within the rule" can both be '
                       'true and neither explains the other. And the regulation carries '
                       '%s limits on adults anywhere: this build searches its full text '
                       'for %s phrasings of individual support — "one-to-one", '
                       '"1:1", "individual aide" among them — on every run, and '
                       'publishes the count beside the result.'
                       % (C.num(sub_aide), C.num(1 + ROOM_EXTRA_IEP_AIDES),
                          C.num(ROOM_EXTRA_IEP_AIDES), C.num(sub_aide),
                          C.num(silent_total), C.num(len(silent))),
                figures={
                    'students': figure(sub_aide, C.num(sub_aide), 'children'),
                    'adults': figure(1 + ROOM_EXTRA_IEP_AIDES,
                                     C.num(1 + ROOM_EXTRA_IEP_AIDES), 'aides'),
                    'iep': figure(ROOM_EXTRA_IEP_AIDES, C.num(ROOM_EXTRA_IEP_AIDES),
                                  'aides assigned by an IEP'),
                    'caps': figure(silent_total, C.num(silent_total),
                                   'limits on adults in the room'),
                    'terms': figure(len(silent), C.num(len(silent)), 'phrasings'),
                },
                allow=('1:1',),
                kind='measured', bearing='sizes', figure='caps',
                basis='Every class-size clause, read for what it counts; a worked room '
                      'checked back against the tier it satisfies on every build; and a '
                      'search of the full text of 603 CMR 28.00 for eight phrasings of '
                      'individual support, published beside the result.',
                not_shown='The corner of it. Where a group of %s has exactly ONE aide and '
                          'that aide is assigned to a single child, nothing says whether '
                          'they also satisfy the tier: the regulation says "assisted by '
                          'one aide" and defines neither the aide nor their duties. '
                          'Assuming they do understates the staffing a group needs; '
                          'assuming they do not overstates it. The document does not say, '
                          'and this page does not choose. Registered as a gap.'
                          % C.num(sub_aide),
            ),
            conclusion(
                id='labels-share-the-axis',
                claim='DESE counts placements on the same axis the rule uses: time '
                      'outside general education',
                so_what='Its "Substantially Separate" label and 28.06(6)(d) both turn '
                        'on the same %d%% threshold.' % threshold,
                detail='The SIMS data handbook defines element DOE034 value 40 as '
                       '"%s". The regulation governs settings "serving solely students '
                       'with disabilities for more than 60%% of the students’ school '
                       'schedule". The two are cut on the same axis, which is what makes '
                       'the counts on this page comparable to the rule at all — and '
                       'is also as far as the comparability goes, because the regulation '
                       'binds a GROUP and DOE034 labels a CHILD.'
                       % sub_def['definition'],
                figures={
                    'threshold': figure(threshold, '%d%%' % threshold),
                },
                allow=('DOE034', '28.06(6)(d)', '40'),
                kind='measured', bearing='sizes', figure='threshold',
                basis='DESE’s SIMS data handbook, element DOE034; and 603 CMR '
                      '28.06(6)(d).',
                not_shown='That the two count the same population. The regulation applies '
                          'to eligible students aged five and older and has separate '
                          'rules for three- and four-year-olds; DOE034 covers ages 6 to '
                          '21 and a different element covers ages 3 to 5. Those are not '
                          'the same line.',
            ),
            conclusion(
                id='how-many-are-in-scope',
                claim='DESE reports %s of Lunenburg’s %s students with disabilities '
                      'as substantially separate' % (C.num(p['sub']['count']),
                                                     C.num(p['total'])),
                so_what='That is the group 28.06(6)(d) covers. It is children, not '
                        'groups, so it sets no staffing number.',
                detail='In FY%d, %s of %s — %s. Two things about that count before '
                       'anybody divides it by eight. It is a count of CHILDREN and the '
                       'rule binds GROUPS. And DESE’s Placement breakdown is '
                       'in-district only: its four printed categories account for %s of '
                       'the %s, with %s children in none of them: the breakdown is '
                       'in-district only, and element DOE034 allows %s placements where '
                       'this prints four.'
                       % (p['fy'], C.num(p['sub']['count']), C.num(p['total']),
                          C.pct(p['sub']['pct']), C.num(p['named']), C.num(p['total']),
                          C.num(p['unnamed']), C.num(len(values))),
                figures={
                    'sub': figure(p['sub']['count'], C.num(p['sub']['count']),
                                  'children'),
                    'total': figure(p['total'], C.num(p['total']), 'children'),
                    'pct': figure(p['sub']['pct'], C.pct(p['sub']['pct'])),
                    'named': figure(p['named'], C.num(p['named']), 'children'),
                    'unnamed': figure(p['unnamed'], C.num(p['unnamed']), 'children'),
                    'values': figure(len(values), C.num(len(values)),
                                     'placement values'),
                    'fy': figure(p['fy'], C.fy(p['fy'])),
                },
                allow=('DOE034', '28.06(6)(d)'),
                kind='measured', bearing='sizes', figure='sub',
                basis='DESE’s special education program characteristics file, '
                      'Placement rows for Lunenburg, most recent year published.',
                not_shown='How those children are grouped, which is the only thing that '
                          'would connect them to the rule. Nothing published says it.',
            ),
        ]),
        'not_established': [
            'How many special education instructional groups Lunenburg runs, how large '
            'each is, or which children are in which. That list is what the regulation '
            'actually binds, and no published document contains it — so no staffing '
            'number follows from anything on this page.',
            'That an "aide" in the regulation is a "paraprofessional" in DESE’s '
            'staffing files or in the district’s budget. 603 CMR 28.02(3) defines a '
            'certified special educator and defines no counterpart; the word '
            'paraprofessional appears in the regulation only in the staff-training '
            'clauses, one of which names teachers, paraprofessionals and teacher '
            'assistants as three separate things.',
            'Whether any Lunenburg group is at, under or over any of these maximums. '
            'Nothing in this archive reports a group size, and nothing on this page is a '
            'compliance finding.',
            'How DESE’s placement label was assigned to any individual child. It is '
            'reported by the district at a census date on element DOE034, and the '
            'percentage-of-time judgement behind each one is not published.',
            'What any of it costs. A placement label is not a dollar and a group size is '
            'not a budget line — the money is a different report, at a different grain.',
        ],
        'closes': 'The district’s own list of special education instructional groups '
                  'by school and setting, with the students and the staff assigned to '
                  'each — the list compiled for DESE’s program approval under 603 '
                  'CMR 28.09 and not published anywhere.',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()
    rel = os.path.relpath(OUT, ROOT)

    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % rel)
            return 1
        with open(OUT, encoding='utf-8') as fh:
            have = json.load(fh)
        if have != data:
            print('STALE %s — run: python3 scripts/build_sped_regulation.py' % rel)
            return 1
        print('ok — the class-size rule reproduces from the regulation and the database')
        return 0

    os.makedirs(PUB, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print(rel)
    print('  %d tiers across %d age bands, one educator in every one:'
          % (len(data['tiers']), len(data['bands'])))
    for b in data['bands']:
        print('    %-14s (%s, %r): %s' % (
            b['band'], b['ages'], b['role'], '; '.join(
                '%d students / %d aide(s) [%s]'
                % (t['students'], t['aides'], t['separateness'])
                for t in data['tiers'] if t['band'] == b['band'])))
        print('      ceiling falls %d -> %d as the setting gets more separate (%d)'
              % (b['top'], b['sub'], b['drop']))
    print('  mid-year allowance +%d students; age range %d months'
          % (data['midyear_extra'], data['age_months']))
    pl = data['placement']
    print('  FY%d: %d of %d substantially separate; the four printed categories account '
          'for %d, leaving %d in none' % (pl['fy'], pl['sub']['count'], pl['total'],
                                          pl['named'], pl['unnamed']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
