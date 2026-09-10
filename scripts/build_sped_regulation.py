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

def tiers(cl, whole):
    """The group-size tiers, parsed out of the two sentences that state them.

    NOTHING HERE IS TYPED. Each row's student count, its educator count and its aide count
    come out of the clause's own words, and the shape of each sentence is asserted -- three
    tiers in (c), two in (d), exactly one certified special educator in every one of them.
    That last assertion is the answer to the question anybody laying this out asks first:
    the teacher count never changes, and what a larger group buys is an aide."""
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
            students=count(students), educators=1,
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
            students=count(students), educators=1,
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
    if {r['educators'] for r in rows} != {1}:
        fail('a tier no longer names exactly one certified special educator, which is the '
             'shape the whole table is built to show')

    # Young children. A different clause, different words -- `teacher` rather than
    # `certified special educator` -- and the row carries the clause's own wording rather
    # than being normalised into the rows above, because nothing here establishes that a
    # teacher in 28.06(7) is a certified special educator in 28.06(6).
    e = cl['28.06(7)(e)']['text']
    m = re.search(r'class size shall not exceed (\d+) with ([a-z]+) teacher and ([a-z]+) '
                  r'aide and no more than ([a-z]+) students with disabilities', e)
    m2 = re.search(r'students with disabilities is ([a-z]+) or ([a-z]+) then the class '
                   r'size may not exceed (\d+) students with ([a-z]+) teacher and '
                   r'([a-z]+) aide', e)
    if not m or not m2:
        fail('28.06(7)(e) no longer states the integrated preschool class sizes in the '
             'two sentences this parses')
    young = [
        dict(setting='Young children, integrated setting (ages three and four)',
             short='Integrated preschool', cite=cl['28.06(7)(e)']['cite'],
             students=int(m.group(1)), educators=count(m.group(2)),
             aides=count(m.group(3)),
             staff='%s teacher and %s aide, with no more than %s of the %s children '
                   'having disabilities' % (m.group(2), m.group(3), m.group(4),
                                            m.group(1)),
             swd_cap=count(m.group(4))),
        dict(setting='Young children, integrated setting (ages three and four)',
             short='Integrated preschool', cite=cl['28.06(7)(e)']['cite'],
             students=int(m2.group(3)), educators=count(m2.group(4)),
             aides=count(m2.group(5)),
             staff='%s teacher and %s aide, where %s or %s of the children have '
                   'disabilities' % (m2.group(4), m2.group(5), m2.group(1), m2.group(2)),
             swd_cap=count(m2.group(2))),
    ]
    f = cl['28.06(7)(f)']['text']
    m3 = re.search(r'limit class sizes to ([a-z]+) students with ([a-z]+) teacher and '
                   r'([a-z]+) aide', f)
    if not m3:
        fail('28.06(7)(f) no longer states the substantially separate preschool class size')
    young.append(dict(
        setting='Young children, substantially separate (ages three and four)',
        short='Substantially separate preschool', cite=cl['28.06(7)(f)']['cite'],
        students=count(m3.group(1)), educators=count(m3.group(2)),
        aides=count(m3.group(3)),
        staff='%s teacher and %s aide' % (m3.group(2), m3.group(3)), swd_cap=None))

    # The two provisions that move a row rather than making one.
    mid = re.search(r'increase the size of an instructional grouping by no more than '
                    r'([a-z]+) additional students', cl['28.06(6)(e)']['text'])
    age = re.search(r'shall not differ by more than (\d+) months',
                    cl['28.06(6)(f)']['text'])
    if not mid or not age:
        fail('28.06(6)(e) or (f) no longer states its own limit in the words this parses')

    return rows, young, count(mid.group(1)), int(age.group(1))


# ------------------------------------------------------ how DESE's labels are defined

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
    main, young, midyear, age_months = tiers(cl, whole)
    codes, ages, values = doe034()
    p = placements(db)
    gaps = gap_rows()

    sub_cap = min(r['students'] for r in main
                  if r['short'] == 'Substantially separate')
    sub_aide = max(r['students'] for r in main
                   if r['short'] == 'Substantially separate')
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
        'tiers': main,
        'young': young,
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
                claim='Every tier in the rule names one certified special educator. Only '
                      'the aides scale',
                so_what='So the rule buys a bigger group with an aide, never with a '
                        'second teacher — in all %s tiers.' % C.num(len(main)),
                detail='Across both settings the regulation states five group-size tiers, '
                       'and the phrase in every one of them is a certified special '
                       'educator, singular. What changes between 8 and 12, and between 12 '
                       'and 16, is an aide. The build refuses to publish this table if a '
                       'tier ever names a second educator, because the shape is the '
                       'finding.',
                figures={
                    'tiers': figure(len(main), C.num(len(main)), 'group-size tiers'),
                    'low': figure(sub_cap, C.num(sub_cap), 'students'),
                    'mid': figure(sub_aide, C.num(sub_aide), 'students'),
                    'high': figure(part_cap, C.num(part_cap), 'students'),
                },
                kind='measured', bearing='sizes', figure='tiers',
                basis='603 CMR 28.06(6)(c) and (d), parsed tier by tier out of the two '
                      'sentences that state them.',
                not_shown='What an aide is. The regulation says "aide" and never defines '
                          'it; DESE’s staffing files and the district’s budget '
                          'lines say "paraprofessional". Nothing here establishes that '
                          'the two words name the same job.',
            ),
            conclusion(
                id='third-tier-one-clause',
                claim='A %s-student tier exists only below the %d%% threshold. Above it '
                      'the rule stops at %s'
                      % (C.num(part_cap), threshold, C.num(sub_aide)),
                so_what='The more separate the room, the LOWER the ceiling. That is the '
                        'opposite of what most people assume.',
                detail='28.06(6)(c) governs groups outside general education 60% or less '
                       'of the schedule and runs to "16 students if the certified special '
                       'educator is assisted by two aides". 28.06(6)(d), for settings '
                       'above that threshold, names two tiers and stops. The phrase "two '
                       'aides" occurs exactly once in the whole of 603 CMR 28.00, which '
                       'this build asserts on every run.',
                figures={
                    'high': figure(part_cap, C.num(part_cap), 'students'),
                    'mid': figure(sub_aide, C.num(sub_aide), 'students'),
                    'threshold': figure(threshold, '%d%%' % threshold),
                },
                allow=('603 CMR 28.00', '28.06(6)(c)', '28.06(6)(d)'),
                kind='measured', bearing='sizes', figure='high',
                basis='The two clauses, parsed; and a count of the phrase "two aides" '
                      'across the full regulation.',
                not_shown='Why. The regulation gives no reason for the asymmetry and this '
                          'page offers none — any explanation would be a hypothesis '
                          'about a drafting decision nobody here witnessed.',
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
    print('  %d tiers: %s' % (len(data['tiers']), '; '.join(
        '%s — %d students, %d educator, %d aide(s)'
        % (t['short'], t['students'], t['educators'], t['aides'])
        for t in data['tiers'])))
    print('  %d young-children rows; mid-year allowance +%d students; age range %d months'
          % (len(data['young']), data['midyear_extra'], data['age_months']))
    pl = data['placement']
    print('  FY%d: %d of %d substantially separate; the four printed categories account '
          'for %d, leaving %d in none' % (pl['fy'], pl['sub']['count'], pl['total'],
                                          pl['named'], pl['unnamed']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
