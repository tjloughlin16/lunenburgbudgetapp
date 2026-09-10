#!/usr/bin/env python3
"""The athletics drill-in page's series, pre-rendered from the database.

    python3 scripts/build_athletics_charts.py            # write it
    python3 scripts/build_athletics_charts.py --check    # fail if it is stale

WHY A FILE AND NOT A QUERY. Everything here is the same for every reader until the
database is rebuilt, and D1's free tier stops at 5 million rows read a day. The page
fetches one static JSON and never touches /api/query.

THREE QUANTITIES, NEVER ADDED. `athletics_history` holds a general fund APPROPRIATION,
a revolving fund's SPENDING, and that fund's REVENUE, and a published figure of
"$335,856 through the revolving fund" was once the second plus the third. Revenue rows
are the ones whose `item` begins `REVENUE`; they are pulled out first, kept in their own
field, and `assert_no_revenue_in_spending()` refuses to write if one ever leaks into a
spending total.

RULE 11 IS THE SUBJECT. A general fund athletics line is what the town has to raise after
the fee-funded fund has paid its share, and athletics is the ONE programme where the
second half is visible. So the comparison this page exists to draw -- appropriation
against what the district's own operating workbook says the sports cost -- is a
measurement of rule 11 rather than a warning about it. It is one year, one programme, and
comparable categories only; the page says all three.

RULE 13. Every figure is recomputed from the tables rather than read off the analyses.
Where the recomputation disagrees with a sentence in `athletics.md` or
`athletics-ledger.md`, the disagreement is CARRIED IN THE PAYLOAD (`recomputed`) and
rendered on the page beside the figure, with which one is the recomputed one. Two are
known and both come from the same place: three FY2024 general fund rows were withdrawn in
commit 07aa298 as a column-mapping error after those documents were written.

WHAT IT REFUSES TO WRITE ON. Four checks, each one guarding a join that could silently
match nothing:
  1. the workbook's cost categories must sum to its own `Total Expenses`, per year, to
     the cent -- it is the source's own identity and it fixes the category split;
  2. the fund's cashbook must chain, each year's closing to the next year's printed
     `SOY BAL` -- the town's own row, not ours;
  3. every series must be non-empty;
  4. no revenue row may reach a spending total.
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import sys

# The conclusions this report states, as DATA rather than as sentences in a page. See
# scripts/conclusions.py.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/athletics.json')
REPORTS = os.path.join(ROOT, 'fy28/public/data/reports.json')

CENT = 0.005

# The workbook's cost columns, grouped for the chart. Three named categories carry the
# bulk of both years and each is separately interesting -- coaches because the general
# fund pays part of it, transportation because it MOVED, officials because the general
# fund budgets zero for it. Everything else is a residual and is drawn achromatic for
# that reason.
#
# `Assignor` and `Police/ EMS` sit in the residual rather than under Officials, even
# though a reader would file them there. That is deliberate: `athletics-ledger.md` §5
# groups them that way, and regrouping them would put a second difference into a table
# whose whole job is to isolate ONE -- the general fund side. The category is the
# workbook's own column name, `Official`, not our idea of what officiating costs.
CATEGORY = {
    'Coaches': 'Coaches',
    'Transportation': 'Transportation',
    'Official': 'Officials',
}
CAT_ORDER = ['Coaches', 'Transportation', 'Officials', 'Everything else']
COST_METRICS = ['Coaches', 'Transportation', 'Official', 'Assignor', 'Police/ EMS',
                'Uniforms', 'Equipment', 'Equipment Recon', 'Dues & Fees', 'Misc']

# The fee-category columns that hold COUNTS in every year they appear. The reduced-fee
# columns are deliberately absent: `HS Red Fee` totals 213 in FY2024 and 662.5 in FY2025,
# so it is dollars in one year and something else in the other, and rule 13 says a column
# whose meaning we cannot state is not a column we may sum.
COUNT_COLUMNS = ['Full Pay', '2nd Sibling', '3rd sibling', 'Full Waiver']

# The general fund lines the district's workbook also tracks, so the two can be set side
# by side. Everything outside this map is reported separately as UNMATCHED rather than
# folded in -- the athletic director, the trainer and insurance are real appropriations
# the workbook simply does not carry, and adding them to one side of a comparison the
# other side cannot see is the error this whole page is about.
COMPARABLE = {
    'Athletic Coaches': 'Coaches',
    'Freshman & MS Coaches': 'Coaches',
    'Freshman & Ms Coaches': 'Coaches',
    'Unified Sports Coach': 'Coaches',
    'Unified Sports,Track/Basketball Coach': 'Coaches',
    'Athletic Transportation': 'Transportation',
    'Athletic Officials': 'Officials',
    'Athletic Replacement of Uniforms': 'Uniforms',
    'Athletic Dues & Fees': 'Everything else matched',
    'Athletic Equipment/Reconditioning': 'Everything else matched',
    'Athletic New Equipment': 'Everything else matched',
    'Special Detail/Athletic Events': 'Everything else matched',
    'Athletic Expenses/Supplies': 'Everything else matched',
}
WORKBOOK_COMPARABLE = {
    'Coaches': ['Coaches'],
    'Transportation': ['Transportation'],
    'Officials': ['Official'],
    'Uniforms': ['Uniforms'],
    'Everything else matched': ['Equipment', 'Equipment Recon', 'Dues & Fees', 'Misc',
                               'Assignor', 'Police/ EMS'],
}
COMPARE_FY = 2024

# ---------------------------------------------------------------------------------------
# WHAT COUNTS AS ATHLETICS, ACCORDING TO THE MACHINE THAT KEEPS THE BOOKS
#
# TJ, on this page: *"I am not clear if you are factoring in some other costs that the
# school does, like the athletic director, trainer, facility costs, etc"*. That is the
# right question and the page could not answer it, because the answer was a comment in
# this file rather than a thing on the page.
#
# It is answerable exactly, and not by us deciding what athletics ought to include. MUNIS
# codes every school account to a FUNCTION and a PROGRAM, and function 3510 is Athletics --
# the same code DESE uses in its own chart of accounts, so the town's ledger and the
# state's expenditure report are naming the same box. Everything the town's accounting
# system considers athletics is in there and nothing else is.
#
# RULE 13a, AND THIS IS THE STRONGEST FORM OF IT THE PAGE HAS. A MUNIS `glytdbud` printout
# is a record of what the books say; the district's budget book and its by-sport workbook
# are figures people assembled. Here the printout AGREES with the budget book to the cent
# -- twelve accounts summing to the same total as the twelve athletics lines in the budget
# book -- which is a cross-check rather than a fourth figure, and the build refuses to
# publish the block if the two ever stop tying.
#
# AND THE OTHER HALF: WHAT NO DOCUMENT CAN ATTRIBUTE. Grounds, custodians, heating,
# electricity and building maintenance are their own functions in the same ledger, whole
# school and whole year, and NOT ONE of those accounts carries the athletics program
# segment. So the pitch, the gym, the lights and the person who lines the field are real
# costs of school sports that nothing published splits out. A total for athletics is
# therefore a FLOOR, and this block is what lets the page say so with the arithmetic
# beside it instead of as an apology.
LEDGER_FY = 2026
ATH_FUNCTION = '3510'
# Where the pieces of a MUNIS account string sit. `0100-3-300-3510-06-6-67-1-511026` is
# fund, ?, department, FUNCTION, location, ?, PROGRAM, ?, object. Named rather than
# indexed inline, because a positional read with no name on it is the defect rule 13
# describes: `v1` meaning "the first column that held figures".
SEG_FUNCTION, SEG_PROGRAM = 3, 6
SCHOOL_ACCOUNT_PREFIX = '0100-3-300-'
# The operations-and-maintenance functions in the school department, with the names DESE
# gives those codes. Read off the ledger rather than listed as a set to sum, so a function
# the town starts using appears here without anybody remembering to add it -- the check
# below is that none of them is athletics-coded, and a function omitted from a hand-kept
# list is a function that check never looked at.
FACILITY_FUNCTION_NAMES = {
    '4110': 'Custodial services',
    '4120': 'Heating of buildings',
    '4130': 'Utility services',
    '4210': 'Maintenance of grounds',
    '4220': 'Maintenance of buildings',
    '4230': 'Maintenance of equipment',
    '4300': 'Extraordinary maintenance',
    '4400': 'Technology infrastructure and maintenance',
    '4450': 'Technology maintenance',
}

# ---------------------------------------------------------------------------------------
# THE FLAG THAT SITS ABOVE THE THREE LEVELS. Where the figures a page publishes have been
# publicly contested on the record, the page says so beside them. The per-sport costs here
# come from ONE document -- the district's own athletics workbook -- and School Committee
# minutes of 24 June 2026 record a resident telling the committee that questions about what
# middle school athletics actually costs have been answered inconsistently.
#
# RULE 15a. A quote from the minutes is asserted against the minutes file on EVERY build,
# not read once and typed. The assertion is on the WORDS, normalised for the line wrapping
# the PDF extract carries, and the line number the quote starts on is computed and
# published so a reader can find it in the text we serve.
#
# RULE 13, WHICH IS WHY THE SPEAKER IS CHECKED TOO. This is public comment, recorded in the
# minutes -- it is a resident's statement, not the district's own words, and the difference
# matters. So the build also asserts that the quote sits inside that speaker's block, and
# the page attributes it that way. What the minutes establish is that the question was put
# in public and that the answers given were described on the record as inconsistent. They
# are not the district conceding a figure.
MINUTES_DOC = 'sources/meetings/text/school-committee/2026-06-24-minutes-7869.txt'
MINUTES_URL = '/docs/minutes/text/school-committee/2026-06-24-minutes-7869.txt'
MINUTES_TOWN_URL = ('https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/'
                    '_06242026-7869')
MINUTES_BOARD = 'School Committee'
MINUTES_DATE = '24 June 2026'
MINUTES_SPEAKER = 'Chris Hurlbut'
# How far the speaker's name may sit ahead of a quote for the quote to be inside their
# block. The whole statement runs a few hundred characters; anything past this and the
# attribution is a guess rather than a reading.
SPEAKER_WINDOW = 2000
MINUTES_QUOTES = [
    ('Community members have asked straightforward questions regarding the actual cost '
     'of middle school athletics and the process required to apply community raised '
     'funds towards these programs. Yet the answers have been inconsistent.'),
    ('Available data suggests that user registration fees may exceed the known cost of '
     'operating these programs'),
    ('middle school athletics were eliminated as a budget reduction of $14,415'),
]
# The reduction the minutes name is also a line in the district's own budget: the build
# checks the two against each other rather than letting a quoted figure stand alone.
MINUTES_REDUCTION_LINE = 'Freshman & MS Coaches'

# THE OTHER QUOTE, AND IT IS THE EVIDENCE FOR THE GAP RATHER THAN FOR A FIGURE.
#
# Rule 15a says to search the meeting archive for what people said about the thing in the
# same year, and it earned itself again here. The claim that no document attributes a share
# of the fields to athletics is a claim about an ABSENCE, and an absence is the hardest
# thing to publish honestly -- so the strongest corroboration available is a town official
# asking for exactly that document in public and being told somebody would look into it.
#
# It is a Cemetery Commission meeting, which is the sort of place nobody would think to
# look and precisely why the archive is searched by term rather than by board.
FIELDS_DOC = 'sources/meetings/text/cemetery-commission/2024-05-16-minutes-6574.txt'
FIELDS_URL = '/docs/minutes/text/cemetery-commission/2024-05-16-minutes-6574.txt'
FIELDS_TOWN_URL = ('https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/'
                   '_05162024-6574')
FIELDS_BOARD = 'Cemetery Commission'
FIELDS_DATE = '16 May 2024'
FIELDS_SPEAKER = 'Michael Clark'
# The quote begins with the speaker's own name because that is how the minutes write it.
# Rendering it as `{speaker} + {quote}` produced “Michael Clark asked what is…” inside
# quotation marks, and the minutes say “Commissioner Michael Clark, asked what is…” --
# a stitched string presented as a quotation, which is rule 13 exactly.
FIELDS_QUOTES = [
    ('Commissioner Michael Clark, asked what is the School Departments field maintenance '
     'plan look like? Do they have a schedule and licenses? DPW Director, Bernard will '
     'look into this'),
]

# THE PERSONA REVIEW'S OWN FINDING, and it is step 3 of notes/process/PERSONAS.md rather
# than anything a verifier could reach: for every category a report shows underspending,
# search the archive for what somebody asked for in the same year.
#
# This page prints two athletics equipment accounts. In the same fiscal year, at the same
# School Committee meeting the page already quotes, a booster president said the team had
# more heads than helmets. The report holds both halves and had not put them together --
# which is exactly the failure that first run of the persona review caught.
#
# WHAT IT MUST NOT BECOME. "The money was there and they would not spend it." The persona
# document is explicit about that: the request may have arrived after the order window,
# reconditioning is not buying, and this ledger is period 12 rather than a closed year.
# The honest sentence puts the two side by side and says what neither establishes.
HELMETS_SPEAKER = 'Nikki Jeannotte'
HELMETS_QUOTES = [
    ('Casey, the head coach put in a request to the athletic department to purchase five '
     'new helmets earlier this spring, we currently have more heads than we have helmets'),
]
EQUIPMENT_ACCOUNTS = ('EQUIP RECO', 'NEW EQUIP')

# THE SEQUEL TO THE HELMETS, AND RULE 8 IS THE REASON IT IS HERE.
#
# The page prints a booster president saying in June that the team had more heads than
# helmets and had heard nothing back. Left there, that is a page that finds fault and
# stops -- which persona 1 will read as advocacy and persona 3 as an ambush. Five weeks
# later football helmets are on the School Committee's own published agenda.
#
# WHAT IT ESTABLISHES AND WHAT IT DOES NOT. It establishes that the subject reached the
# committee's agenda under New Business, as a donation, on a date. It does not establish
# that the request was approved, that the helmets were bought, who paid, or that the two
# items are the same helmets. An agenda is a list of what will be discussed, and this
# archive holds no minutes for that meeting, so the outcome is not readable here at all.
AGENDA_DOC = 'sources/meetings/text/school-committee/2026-07-29-agenda-7930.txt'
AGENDA_URL = '/docs/minutes/text/school-committee/2026-07-29-agenda-7930.txt'
AGENDA_TOWN_URL = ('https://www.lunenburgma.gov/AgendaCenter/ViewFile/Agenda/'
                   '_07292026-7930')
AGENDA_DATE = '29 July 2026'
AGENDA_QUOTES = [
    'Donation-Football Helmets & Transportation',
]

# THE PER-SPORT QUESTION, PUT IN PUBLIC BY A PARENT WHO HAD DONE THE ARITHMETIC HIMSELF.
#
# Rule 15a's step 3 -- search the archive for what people said about the thing in the same
# year -- found this and it is the single most useful thing the search returned. The page
# sets three documents side by side and says a resident choosing which team to give up is
# choosing between figures that disagree by a multiple. On 24 June 2026 a resident stood up
# and described exactly that, from the other end: he had found the FY24 by-sport figures in
# the town's own budget files, escalated them himself, and then could not reconcile the
# result with what he had watched two seasons of middle school sport actually consume.
#
# WHY IT BELONGS ON THIS PAGE RATHER THAN ANY OTHER. The sport he names is TRACK, and
# Outdoor Track is the widest disagreement in the archive after Boys' Lacrosse -- three
# documents, three figures, one year. He also reaches for the words `programmatic cost`,
# which is the literal heading of one of the three columns. That is a resident and a
# document using one phrase, and it is the closest anything in this archive comes to
# saying what one of the three columns counts.
#
# RULE 7, AND IT BITES HARD HERE. What the minutes establish is that a resident said these
# things in public. They do not establish what track cost, what a programmatic cost is, or
# that his reading of the column is the district's. His definition is a hypothesis offered
# by a member of the public; the page says so beside it, and nothing on the page is
# computed from it.
BYSPORT_SPEAKER = 'Matt Nazarenko'
BYSPORT_QUOTES = [
    ('Field hockey and track, they are using hand me down jerseys, field hockey had 11 '
     'games last year and one official per game at $50 per official. Track had zero '
     'officials, the coaches were the officials and they are using hand me down jerseys '
     'from varsity.'),
    ('I don’t know how track costs anything other than overhead allocations, which I '
     'would call programmatic cost.'),
    ('I have put in a formal request records to Dr. Fortuna and the school to help out, '
     'I would like the actuals for this.'),
]

# WHAT WAS SEARCHED FOR, IN THE TOWN'S VOCABULARY RATHER THAN OURS.
#
# The lesson is /what-courses-actually-ran's: `foreign language` returned nothing useful
# and `French` returned the parent. So this list is what residents in Lunenburg say about
# sport -- helmets, jerseys, boosters, the fee under three different names -- and not the
# nouns this project uses for the same things. `programmatic cost` is here because it is
# the one term a document and a resident share.
#
# THE COUNT IS PUBLISHED WITH ITS DENOMINATOR, and that is the point of printing it at all.
# A search that finds nothing prints nothing, and nothing reads as `nobody said it`. It is
# not: it means nobody said it in the documents that can be READ, and three quarters of
# this archive is readable.
SEARCHED = ['helmets', 'jersey', 'booster', 'athletic fee', 'user fee', 'pay to play',
            'middle school athletics', 'programmatic cost', 'officials']

# The generic words in the workbook's sport names. They are not sports, so a payment
# reading "MS" or "OOD" is not a payment attributed to a sport, and counting one as a hit
# would turn a real absence into a false presence.
SPORT_STOPWORDS = {'boys', 'girls', 'out', 'of', 'district', 'team', 'ood', 'hs', 'ms'}
# Every field on a cashbook row that carries free text or a reference. A disbursement is
# searched across all of them: the claim is that NOTHING on the row names a sport, and a
# claim about the whole row has to look at the whole row.
JOURNAL_TEXT_FIELDS = ('src_meaning', 'journal', 'ref1', 'po_ref2', 'ref3', 'reference',
                       'check_no', 'warrant', 'voucher', 'vendor', 'comments')

# The two documents this page draws, quoted so a reader can find them.
RELATED = [
    ('athletics', 'The written analysis: both sides of the money, FY14 to FY26, and why '
                  'an appropriation is not a cost'),
    ('athletics-ledger', 'Three years of the fund at transaction level — 277 postings '
                         'with vendor, check number and the clerk’s own comments'),
]


def q(c, sql, *a):
    return [dict(r) for r in c.execute(sql, a)]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fail(msg):
    sys.exit(f'build_athletics_charts: {msg}')


def _flat(text):
    """One run of whitespace is one space.

    The minutes reach us as text extracted from a PDF, so a sentence is wrapped across
    lines at whatever width the page had. Asserting a quote against the raw file would be
    asserting the line breaks, which are the extractor's and not the committee's.
    """
    return ' '.join(text.split())


def minutes_quotes(doc=None, speaker=None, quotes=None, window=None):
    """Every quote this page prints, checked against the minutes file. Rule 15a.

    Returns the quote with the line of the file it starts on. Refuses to write if a quote
    is not there verbatim, or if it does not sit inside the block of the speaker the page
    attributes it to -- a quote lifted out of the wrong speaker's remarks is exactly the
    rule 13 failure of quoting a rendering rather than the source.
    """
    doc = doc or MINUTES_DOC
    speaker = MINUTES_SPEAKER if speaker is None else speaker
    quotes = quotes or MINUTES_QUOTES
    # HOW FAR IS TOO FAR, PER SPEAKER RATHER THAN GLOBALLY. The default window is sized
    # for a short public comment. One statement on this page runs the length of a page and
    # a half, so a window that fits it is stated at the call site with the reason, rather
    # than the global being widened for everybody -- a limit relaxed for one case and left
    # relaxed is a check that has stopped checking.
    window = SPEAKER_WINDOW if window is None else window
    path = os.path.join(ROOT, doc)
    if not os.path.exists(path):
        fail(f'{doc} is not on disk — run scripts/sync_archive.py --pull. '
             'A quote this page prints is asserted against it on every build.')
    raw = open(path, encoding='utf-8').read().splitlines()

    # A normalised copy of the file, and the line each normalised character came from, so
    # a hit can be reported as a coordinate rather than as "it is in there somewhere".
    flat, line_at = [], []
    for n, ln in enumerate(raw, start=1):
        for word in ln.split():
            if flat:
                flat.append(' ')
                line_at.append(n)
            flat.append(word)
            line_at.extend([n] * len(word))
    flat = ''.join(flat)

    # EVERY place the speaker is named, not the first. Minutes name people in the
    # attendance list at the top and again where they speak, so `find` returns a
    # coordinate 5,000 characters from the words -- which reads exactly like a quote
    # attributed to the wrong person. The test is whether the quote sits inside the
    # NEAREST PRECEDING mention of that speaker, which is the thing the claim actually
    # rests on.
    #
    # `speaker=False` means the document HAS no speakers: an agenda is a list of items a
    # board published in advance, and there is no person to attribute a line to. Saying
    # that explicitly is better than inventing an attribution to satisfy a check -- the
    # verbatim assertion still runs, and it is the whole of what an agenda can support.
    speaker_at = ([] if speaker is False
                  else [m.start() for m in re.finditer(re.escape(speaker), flat)])
    if speaker is not False and not speaker_at:
        fail(f'{doc} no longer names {speaker}. The page attributes these '
             'words to that speaker, and an attribution that cannot be checked is not one.')

    out = []
    for quote in quotes:
        at = flat.find(_flat(quote))
        if at < 0:
            fail(f'{doc} no longer contains, verbatim:\n  “{quote}”\n'
                 'Either the town republished the minutes or the extractor changed. '
                 'Nothing is published from a quote that cannot be found in its source.')
        if speaker is False:
            out.append(dict(text=quote, line=line_at[at]))
            continue
        before = [x for x in speaker_at if x <= at]
        gap = at - before[-1] if before else -1
        if not 0 <= gap <= window:
            fail(f'the quote “{quote[:60]}…” is {gap} characters after the nearest '
                 f'mention of {speaker} in {doc}. The page says it is that '
                 'speaker’s; at that distance it is a guess.')
        out.append(dict(text=quote, line=line_at[at]))
    return out


MEETING_TEXT = 'sources/meetings/text'


def searched():
    """How many meeting documents use each of the town's own words for sport, and out of
    how many that can be read at all.

    THE DENOMINATOR IS THE POINT. A grep that finds nothing prints nothing, and nothing
    reads as *nobody said it*. It is not: it means nobody said it in the documents that
    carry text, and a quarter of this archive is image scans awaiting OCR.

    ON A LEADING WORD BOUNDARY, LEADING ONLY. A bare substring match for `Latin` once
    matched 140 documents here through the word `relating`; the true count was four. A
    TRAILING boundary is the opposite and quieter error -- it drops `officials` from a
    search for `official`, and residents write plurals. So the boundary goes on the front
    and nowhere else.
    """
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here — a search of nothing is not a search')
    readable, dates, published = [], [], 0
    for r in csv.DictReader(open(idx, encoding='utf-8')):
        published += 1
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MEETING_TEXT, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
            if (r.get('date') or '').strip():
                dates.append(r['date'].strip())
    if not readable:
        fail('no meeting document is readable — refusing to publish a count of what '
             'nobody said')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    terms = [dict(term=t,
                  documents=sum(1 for b in bodies
                                if re.search(r'\b%s' % re.escape(t), b, re.I)))
             for t in SEARCHED]
    if not any(t['documents'] for t in terms):
        fail('not one search term matched any document. The archive did not go quiet; '
             'something is wrong with the read.')
    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        fail('sources/data/minutes-searchable.csv is not here — the searchable share '
             'cannot be typed')
    tally = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            tally[k] += int(r[k] or 0)
    if not tally['searchable'] or tally['held'] != tally['searchable'] + tally['unsearchable']:
        fail('minutes-searchable.csv does not reconcile — refusing to publish a coverage '
             'figure that does not add up')
    if not dates:
        fail('no meeting document carries a date — the span cannot be typed')
    return terms, dict(held=tally['held'], searchable=tally['searchable'],
                       unsearchable=tally['unsearchable'],
                       image_scan=tally['image_scan'],
                       text_files_present=len(readable), published=published,
                       first_date=min(dates), last_date=max(dates),
                       searchable_share=round(tally['searchable'] / tally['held'], 4))


def counted(c, budget_book_general, budget_book_items, workbook_unmatched,
            workbook_unmatched_total):
    """What the town's accounting system itself codes to athletics, and what it cannot.

    Two halves, and the page needs both to answer "are you counting the athletic director".

    THE FIRST HALF is every account MUNIS codes to function 3510. It is not our list: it
    is the box the bookkeeping puts things in, and the athletic director, the trainer, the
    secretary, the police detail and the insurance are all inside it. The district's own
    per-sport workbook carries none of those four, which is a large part of why the
    published totals for athletics disagree -- and until now that was a comment in this
    file rather than a sentence a reader could see.

    THE SECOND HALF is the operations-and-maintenance functions in the same ledger. The
    fields, the gym, the lights and the custodians are real costs of running school sports
    and NOT ONE of those accounts carries the athletics program segment, so no share of
    them can be attributed. That makes every athletics total a floor, and this is the
    arithmetic that lets the page say so rather than hedge.
    """
    rows = q(c, "SELECT account, name, original, transfers, revised, expended, doc_id, "
                "period FROM munis_ledger WHERE fy = ? AND totals_only = '0' AND "
                "account LIKE ?", LEDGER_FY, SCHOOL_ACCOUNT_PREFIX + '%')
    if not rows:
        fail(f'no FY{LEDGER_FY} school accounts in munis_ledger — the ledger join matched '
             'nothing, which reads exactly like a school department that spends nothing')

    def seg(acct, i):
        parts = acct.split('-')
        return parts[i] if len(parts) > i else ''

    ath = [r for r in rows if seg(r['account'], SEG_FUNCTION) == ATH_FUNCTION]
    if not ath:
        fail(f'no FY{LEDGER_FY} account carries function {ATH_FUNCTION} — either the '
             'account string changed shape or the town recoded athletics. Nothing is '
             'published from a join that matched nothing.')
    ath_programs = sorted({seg(r['account'], SEG_PROGRAM) for r in ath})

    accounts = sorted(
        (dict(account=r['account'],
              name=r['name'],
              program=seg(r['account'], SEG_PROGRAM),
              appropriated=round(num(r['original']) or 0.0, 2),
              transfers=round(num(r['transfers']) or 0.0, 2),
              revised=round(num(r['revised']) or 0.0, 2),
              # THROUGH PERIOD 12, WHICH IS NOT A CLOSED YEAR. Period 13 is the year-end
              # close after the lapse period and the town has not published one for
              # FY2026. So a low figure here is a line that had not spent YET as much as
              # a line that did not spend, and the page says which.
              expended=round(num(r['expended']) or 0.0, 2))
         for r in ath),
        key=lambda r: -r['appropriated'])
    # THE ACCOUNT'S NAME IN THE OTHER DOCUMENT, where the two documents fix it between
    # them. MUNIS prints a ten-character abbreviation -- `ATHTRAINER`, `ADSALARY` -- and
    # the district's budget book prints a sentence. Where exactly ONE budget book line
    # carries the same appropriation to the cent, the two name the same thing and the
    # readable name is published beside the ledger's own. Where the amounts do not tie,
    # or tie to more than one line, NOTHING is published: a label chosen by resemblance
    # would be us naming the account, which is rule 13's whole subject. Five of the twelve
    # come back empty in FY2026, both because a transfer moved the line after it was
    # appropriated.
    by_amount = collections.defaultdict(list)
    for item, per_fy in budget_book_items.items():
        amt = per_fy.get(LEDGER_FY)
        if amt is not None:
            by_amount[round(amt, 2)].append(item)
    for r in accounts:
        hit = by_amount.get(r['appropriated'], [])
        r['book_line'] = hit[0] if len(hit) == 1 else ''

    appropriated = round(sum(r['appropriated'] for r in accounts), 2)
    revised = round(sum(r['revised'] for r in accounts), 2)
    expended = round(sum(r['expended'] for r in accounts), 2)

    # THE CROSS-CHECK, AND IT IS THE POINT OF THE BLOCK. The accounting system's printout
    # and the district's budget book are two independent statements of the same quantity,
    # and they tie to the cent. Rule 13a: one of them is a record of what the books say and
    # the other is a sheet somebody assembled, so this is the printout confirming the
    # sheet -- not a fourth figure to add to the three the page already publishes.
    book = round(budget_book_general.get(LEDGER_FY, 0.0), 2)
    if not book:
        fail(f'athletics_history carries no FY{LEDGER_FY} general fund total to check the '
             'ledger against')
    if abs(appropriated - book) > CENT:
        fail(f'FY{LEDGER_FY}: function {ATH_FUNCTION} in the ledger appropriates '
             f'{appropriated:,.2f} against {book:,.2f} in the district\u2019s budget book. '
             'The page states that the accounting system and the budget book agree on what '
             'athletics is, and they no longer do.')

    # THE SECOND HALF. Read the facility functions off the ledger rather than summing a
    # hand-kept set: a function the town starts using has to be inside the check, and a
    # function omitted from a list is one the check never looked at.
    fac_rows = [r for r in rows
                if seg(r['account'], SEG_FUNCTION) in FACILITY_FUNCTION_NAMES]
    if not fac_rows:
        fail(f'no FY{LEDGER_FY} school account carries an operations-and-maintenance '
             'function. A school department with no custodians and no heat is an empty '
             'join, not a finding.')
    by_function = collections.defaultdict(float)
    for r in fac_rows:
        by_function[seg(r['account'], SEG_FUNCTION)] += num(r['revised']) or 0.0
    facility = [dict(code=k, name=FACILITY_FUNCTION_NAMES[k], amount=round(v, 2),
                     accounts=sum(1 for r in fac_rows
                                  if seg(r['account'], SEG_FUNCTION) == k))
                for k, v in sorted(by_function.items())]
    facility_total = round(sum(f['amount'] for f in facility), 2)

    # THE ASSERTION THE WHOLE "we cannot say" REST ON. If a facility account ever DOES
    # carry the athletics program segment, then a share IS attributable and the page must
    # stop saying it is not.
    attributed = [r['account'] for r in fac_rows
                  if seg(r['account'], SEG_PROGRAM) in ath_programs]
    if attributed:
        fail('an operations-and-maintenance account now carries the athletics program '
             f'segment: {attributed}. The page states that no facility cost is attributed '
             'to athletics anywhere in the ledger, and that is no longer true.')

    return dict(
        fy=LEDGER_FY,
        function=ATH_FUNCTION,
        period=str(rows[0]['period']),
        doc=rows[0]['doc_id'],
        accounts=accounts,
        appropriated=appropriated,
        revised=revised,
        expended=expended,
        budget_book=book,
        ties=True,
        # The general fund lines the district's own by-sport workbook does not carry at
        # all, in the year the two can be compared. This is the answer to "is the athletic
        # director in there": in the town's appropriation yes, in the per-sport workbook
        # no, and the gap between them is most of why the published totals disagree.
        workbook_fy=COMPARE_FY,
        not_in_workbook=workbook_unmatched,
        not_in_workbook_total=workbook_unmatched_total,
        facility=facility,
        facility_total=facility_total,
        facility_attributed=0.0,
    )


def build():
    if not os.path.exists(DB):
        fail(f'{os.path.relpath(DB, ROOT)} is not here — run scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    # ---------------------------------------------------------------- both sides
    hist = q(c, 'SELECT fy, side, item, amount, basis, source FROM athletics_history')
    if not hist:
        fail('athletics_history is empty')
    spend = collections.defaultdict(lambda: collections.defaultdict(float))
    revenue = collections.defaultdict(float)
    rev_items = collections.defaultdict(dict)
    basis = collections.defaultdict(set)
    items = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in hist:
        fy, amt = int(r['fy']), num(r['amount'])
        if amt is None:
            continue
        if r['item'].startswith('REVENUE'):
            if r['side'] != 'revolving':
                fail(f'a REVENUE row on the {r["side"]} side in FY{fy} — the fund is the '
                     'only side of this whose receipts are published')
            revenue[fy] += amt
            rev_items[r['item']][fy] = amt
            continue
        spend[r['side']][fy] += amt
        items[r['side']][r['item']][fy] = amt
        if r['side'] == 'revolving':
            basis[fy].add(r['basis'])

    years = sorted({int(r['fy']) for r in hist})
    both = []
    for fy in years:
        b = basis.get(fy, set())
        state = ('not published' if not b
                 else 'partial' if b == {'unproven'}
                 else 'published')
        both.append(dict(
            fy=fy,
            general=round(spend['general'].get(fy, 0.0), 2),
            general_basis=('budget' if fy >= 2026 else 'restated actual'),
            revolving=round(spend['revolving'].get(fy, 0.0), 2) if state != 'not published' else None,
            revolving_state=state,
            revenue=round(revenue[fy], 2) if fy in revenue else None))

    # A total is only an all-in total in a year where both sides were published.
    for r in both:
        r['all_in'] = (round(r['general'] + r['revolving'], 2)
                       if r['revolving_state'] == 'published' else None)
        r['fund_share'] = (round(r['revolving'] / r['all_in'], 4)
                           if r['all_in'] else None)

    # RULE-BREAK GUARD. If any revenue figure ever equals a spending figure for the same
    # year, one of them has been folded into the other.
    for r in both:
        if r['revenue'] and r['revolving'] and abs(r['revenue'] - r['revolving']) < CENT:
            fail(f'FY{r["fy"]}: fund revenue and fund spending are the same number — '
                 'one has been added into the other')

    def line(side, name):
        return [dict(fy=fy, amount=round(v, 2))
                for fy, v in sorted(items[side].get(name, {}).items())]

    transport = []
    for fy in years:
        g = items['general'].get('Athletic Transportation', {}).get(fy)
        f = items['revolving'].get('Athletic Transportation', {}).get(fy)
        st = 'published' if f is not None else 'not published'
        transport.append(dict(fy=fy, general=round(g, 2) if g is not None else None,
                              fund=round(f, 2) if f is not None else None, state=st))

    coaching = []
    for fy in years:
        parts = {k: v.get(fy) for k, v in items['general'].items()
                 if COMPARABLE.get(k) == 'Coaches'}
        g = sum(v for v in parts.values() if v is not None)
        f = items['revolving'].get('Athletic Coaches', {}).get(fy)
        coaching.append(dict(
            fy=fy, general=round(g, 2) if any(v is not None for v in parts.values()) else None,
            fund=round(f, 2) if f is not None else None,
            lines=sorted(k for k, v in parts.items() if v is not None)))

    # ---------------------------------------------------- the workbook, by category
    sport = q(c, "SELECT season, level, sport, fy, metric, value, is_numeric, cell "
                 'FROM athletics_by_sport')
    if not sport:
        fail('athletics_by_sport is empty')
    by_cat = collections.defaultdict(lambda: collections.defaultdict(float))
    printed = collections.defaultdict(float)
    metric_tot = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in sport:
        if r['is_numeric'] != '1':
            continue
        v = num(r['value'])
        if v is None:
            continue
        fy = int(r['fy'])
        if r['metric'] == 'Total Expenses':
            printed[fy] += v
        if r['metric'] in COST_METRICS:
            metric_tot[fy][r['metric']] += v
            by_cat[fy][CATEGORY.get(r['metric'], 'Everything else')] += v

    cost_years = sorted(printed)
    if not cost_years:
        fail('no Total Expenses rows — the workbook join matched nothing')
    # CHECK 1: the source's own identity. Every cost column summed must equal the sheet's
    # own Total Expenses column, per year. It does, to the cent, in both years -- which is
    # what fixes the category split as the document's rather than ours.
    for fy in cost_years:
        got = sum(by_cat[fy].values())
        if abs(got - printed[fy]) > CENT:
            fail(f'FY{fy}: cost columns sum to {got:,.2f} against the workbook’s own '
                 f'Total Expenses of {printed[fy]:,.2f} — the category split no longer '
                 'reconciles to the document, so it is not the document’s split')
    categories = [dict(fy=fy, **{k: round(by_cat[fy].get(k, 0.0), 2) for k in CAT_ORDER},
                       total=round(printed[fy], 2)) for fy in cost_years]

    # ------------------------------------------------- participation and cost by sport
    ath = collections.defaultdict(float)
    cost = collections.defaultdict(float)
    for r in sport:
        if r['is_numeric'] != '1':
            continue
        v = num(r['value'])
        if v is None:
            continue
        k = (r['season'], r['level'], r['sport'], int(r['fy']))
        if r['metric'] == 'Total Athletes':
            ath[k] += v
        elif r['metric'] == 'Total Expenses':
            cost[k] += v

    part_years = sorted({k[3] for k in ath})
    by_sport = []
    for (season, level, name, fy), n in sorted(ath.items()):
        cst = cost.get((season, level, name, fy))
        by_sport.append(dict(
            season=season, level=level, sport=name, fy=fy, athletes=n,
            cost=round(cst, 2) if cst is not None else None,
            per_athlete=(round(cst / n, 2) if cst is not None and n > 0 else None)))

    participation = []
    for fy in part_years:
        for season in ('Fall', 'Winter', 'Spring'):
            for level in ('HS', 'MS'):
                n = sum(v for k, v in ath.items()
                        if k[3] == fy and k[0] == season and k[1] == level)
                participation.append(dict(fy=fy, season=season, level=level, athletes=n))
    part_totals = [dict(fy=fy,
                        total=sum(v for k, v in ath.items() if k[3] == fy),
                        hs=sum(v for k, v in ath.items() if k[3] == fy and k[1] == 'HS'),
                        ms=sum(v for k, v in ath.items() if k[3] == fy and k[1] == 'MS'))
                   for fy in part_years]

    # A negative row is the workbook subtracting out-of-district athletes. Counted as the
    # sheet counts them -- but a reader has to be told, because a bar of 649 built partly
    # out of −11 is not a headcount of anything.
    negatives = sorted(
        (dict(fy=k[3], season=k[0], level=k[1], sport=k[2], athletes=v)
         for k, v in ath.items() if v < 0), key=lambda r: (r['fy'], r['season']))

    # -------------------------------------------------------- who pays, by category
    mix, mix_years = [], []
    for fy in part_years:
        counts = {m: sum(num(r['value']) or 0 for r in sport
                         if r['is_numeric'] == '1' and int(r['fy']) == fy
                         and r['metric'] == m)
                  for m in COUNT_COLUMNS}
        if not any(counts.values()):
            continue
        mix_years.append(fy)
        total = sum(v for k, v in ath.items() if k[3] == fy)
        mix.append(dict(fy=fy, total=total,
                        unclassified=round(total - sum(counts.values()), 2),
                        **{m: counts[m] for m in COUNT_COLUMNS}))
    if not mix:
        fail('no fee-category counts — the count-column join matched nothing')

    # ------------------------------------------------------------- the fee schedule
    fees = q(c, 'SELECT fy, school_year, level, item, amount, set_on, source, '
                'source_ref, verified FROM athletic_fee_schedule ORDER BY fy, level, item')
    if not fees:
        fail('athletic_fee_schedule is empty')
    fees = [dict(fy=int(r['fy']), school_year=r['school_year'], level=r['level'],
                 item=r['item'], amount=num(r['amount']), set_on=r['set_on'],
                 source=r['source'], source_ref=r['source_ref'], verified=r['verified'])
            for r in fees]
    headline = [dict(fy=r['fy'], school_year=r['school_year'], level=r['level'],
                     amount=r['amount'], set_on=r['set_on'], source=r['source'])
                for r in fees if r['item'] == 'full_pay']

    # ------------------------------------------------------------- the fund's cashbook
    j = q(c, 'SELECT fy, eff_date, post_date, src, src_meaning, journal, ref1, '
             'po_ref2, ref3, reference, amount, comments, vendor, check_no, warrant, '
             'voucher FROM fund_1301_cash_journal ORDER BY fy, eff_date')
    if not j:
        fail('fund_1301_cash_journal is empty')
    flow, src_rows, opening = [], [], {}
    for fy in sorted({int(r['fy']) for r in j}):
        rows = [r for r in j if int(r['fy']) == fy]
        soy = [r for r in rows if r['src'] == 'SOY']
        if len(soy) != 1:
            fail(f'FY{fy}: {len(soy)} SOY BAL rows — the fund’s own opening balance is '
                 'the row this extract is checked against, and there must be exactly one')
        op = num(soy[0]['amount'])
        opening[fy] = op
        moves = [num(r['amount']) or 0 for r in rows if r['src'] != 'SOY']
        receipts = sum(v for v in moves if v > 0)
        payments = sum(v for v in moves if v < 0)
        journals = sum(num(r['amount']) or 0 for r in rows if r['src'] == 'GEN')
        flow.append(dict(fy=fy, opening=round(op, 2), receipts=round(receipts, 2),
                         payments=round(payments, 2), net=round(receipts + payments, 2),
                         closing=round(op + receipts + payments, 2),
                         journals=round(journals, 2),
                         without_journals=round(op + receipts + payments - journals, 2),
                         postings=len(rows)))
        for src in sorted({r['src'] for r in rows if r['src'] != 'SOY'}):
            src_rows.append(dict(
                fy=fy, src=src,
                meaning=next(r['src_meaning'] for r in rows if r['src'] == src),
                amount=round(sum(num(r['amount']) or 0 for r in rows if r['src'] == src), 2),
                postings=sum(1 for r in rows if r['src'] == src)))

    # CHECK 2: the chain the town prints itself. Our closing balance for one year must be
    # the opening balance the town wrote for the next. It ties to the cent, all three
    # years, and this is the only check on this page the source itself supplies.
    for a, b in zip(flow, flow[1:]):
        if abs(a['closing'] - opening[b['fy']]) > CENT:
            fail(f'FY{a["fy"]} closes at {a["closing"]:,.2f} and FY{b["fy"]} opens at '
                 f'{opening[b["fy"]]:,.2f} — the cashbook no longer chains')

    memo = [dict(fy=int(r['fy']), eff=r['eff_date'], post=r['post_date'],
                 journal=r['journal'], ref1=r['ref1'], reference=(r['reference'] or '').strip(),
                 amount=num(r['amount']), comments=r['comments'])
            for r in j if r['src'] == 'GEN']
    if not memo:
        fail('no GEN rows — the "per memo" join matched nothing')
    memo_total = round(sum(r['amount'] for r in memo), 2)

    # Vendor is populated on receipts and empty on every disbursement row. That absence is
    # a finding, so it is counted rather than described.
    disb = [r for r in j if (num(r['amount']) or 0) < 0]
    named = [r for r in disb if (r['vendor'] or '').strip()]

    # ------------------------------------------ CAN A PAYMENT BE PUT AGAINST A SPORT?
    #
    # The page states that it cannot, so the page runs the search rather than repeating a
    # sentence from an analysis. Every disbursement row, every free-text and reference
    # field on it, against the workbook's OWN sport names -- taken from the data, so a
    # sport the district adds next year is searched for without anybody remembering to.
    #
    # A search that finds nothing and a search that had nothing to look for are the same
    # printed zero, which is why both the vocabulary and the rows are asserted non-empty
    # before the count means anything.
    sport_terms = sorted({
        w for name in {k[2] for k in ath}
        for w in ''.join(ch if ch.isalpha() else ' ' for ch in name.lower()).split()
        if len(w) >= 2 and w not in SPORT_STOPWORDS})
    if not sport_terms:
        fail('no sport names came out of athletics_by_sport, so the search for a sport on '
             'a payment had nothing to look for. A zero from an empty vocabulary is not a '
             'finding.')
    if not disb:
        fail('no disbursement rows in fund_1301_cash_journal — the page says what these '
             'rows do not carry, and it may not say it about an empty set')
    # Whole words only. `CC` is the workbook's name for cross country and it is also
    # inside "accounts payable", so a substring test reported eleven payments as naming a
    # sport when not one of them does -- a false presence, which is worse than the absence
    # it would have hidden.
    term_re = {t: re.compile(r'\b' + re.escape(t) + r'\b') for t in sport_terms}
    sport_hits = []
    for r in disb:
        blob = ' '.join((r[f] or '') for f in JOURNAL_TEXT_FIELDS).lower()
        hit = sorted({t for t, rx in term_re.items() if rx.search(blob)})
        if hit:
            sport_hits.append(dict(fy=int(r['fy']), journal=r['journal'],
                                   amount=num(r['amount']), terms=hit))
    warrant_rows = [r for r in disb if r['src'] == 'APP']
    with_ref = [r for r in warrant_rows if (r['reference'] or '').strip()]
    attribution = dict(
        years=sorted({int(r['fy']) for r in disb}),
        disbursements=len(disb),
        named_vendor=len(named),
        warrant_disbursements=len(warrant_rows),
        warrant_disbursements_referenced=len(with_ref),
        fields_searched=list(JOURNAL_TEXT_FIELDS),
        sport_terms=sport_terms,
        sports=len({k[2] for k in ath}),
        sport_mentions=len(sport_hits),
        sport_hits=sport_hits)

    # ------------------------------------- rule 11, measured: one year, one programme
    gf = collections.defaultdict(float)
    unmatched = collections.defaultdict(float)
    for item, per_fy in items['general'].items():
        v = per_fy.get(COMPARE_FY)
        if v is None:
            continue
        cat = COMPARABLE.get(item)
        if cat:
            gf[cat] += v
        else:
            unmatched[item] += v
    wb = {cat: sum(metric_tot[COMPARE_FY].get(m, 0.0) for m in ms)
          for cat, ms in WORKBOOK_COMPARABLE.items()}
    if not gf or not any(wb.values()):
        fail(f'FY{COMPARE_FY}: the comparable-category join matched nothing on one side')
    compare = dict(
        fy=COMPARE_FY,
        rows=[dict(category=cat, workbook=round(wb.get(cat, 0.0), 2),
                   general=round(gf.get(cat, 0.0), 2),
                   outside=round(wb.get(cat, 0.0) - gf.get(cat, 0.0), 2))
              for cat in ('Officials', 'Coaches', 'Transportation', 'Uniforms',
                          'Everything else matched')],
        workbook_total=round(sum(wb.values()), 2),
        general_total=round(sum(gf.values()), 2),
        unmatched=[dict(item=k, amount=round(v, 2))
                   for k, v in sorted(unmatched.items(), key=lambda kv: -kv[1])],
        unmatched_total=round(sum(unmatched.values()), 2))
    compare['share'] = round(compare['general_total'] / compare['workbook_total'], 4)

    # CHECK 1b: the comparable categories must not exceed the workbook's own total.
    if compare['workbook_total'] > printed[COMPARE_FY] + CENT:
        fail(f'FY{COMPARE_FY}: comparable categories sum above the workbook’s own total')

    # -------------------------------------- THREE DOCUMENTS, THREE FIGURES, ONE YEAR
    #
    # The strongest thing on this page, and it is a DISAGREEMENT rather than a number.
    # Three documents state what athletics came to in FY2024 and no two of them agree:
    #
    #   the district's own workbook          — its printed Total Expenses, every sport
    #   the athletics revolving fund         — what it actually paid out, from its cashbook
    #   the town's general fund              — every athletics line in the budget book
    #
    # The second and third are money that left two different pots, so they may be added to
    # each other -- and their sum is well above what the first says the whole thing cost.
    # The first may NOT be added to either: it is a claim about total cost, and adding a
    # claim to a payment is the error this page exists to demonstrate.
    #
    # Levels, in the sense the site now labels them: the workbook figure is STATED, the
    # fund's payments are TRACED TO A PAYMENT, the appropriation is STATED in a budget book
    # the district wrote. Publishing the three together is what CROSS-CHECKED means when
    # the sources visibly disagree.
    flow_cmp = next((r for r in flow if r['fy'] == COMPARE_FY), None)
    wb_total = printed.get(COMPARE_FY)
    gf_total = spend['general'].get(COMPARE_FY)
    if flow_cmp is None or wb_total is None or not gf_total:
        fail(f'FY{COMPARE_FY}: one of the three sides of the disagreement is missing — '
             f'workbook {wb_total}, fund {flow_cmp is not None}, general fund {gf_total}. '
             'A three-way disagreement with two sides is not one, and an absent side must '
             'not be drawn as a small one.')
    fund_paid = abs(flow_cmp['payments'])
    if fund_paid <= 0:
        fail(f'FY{COMPARE_FY}: the revolving fund shows no payments out. That is an empty '
             'join, not a fund that spent nothing.')
    three_way = dict(
        fy=COMPARE_FY,
        workbook=round(wb_total, 2),
        fund_paid=round(fund_paid, 2),
        general=round(gf_total, 2),
        two_pots=round(fund_paid + gf_total, 2),
        over_workbook=round(fund_paid + gf_total - wb_total, 2),
        over_workbook_share=round((fund_paid + gf_total) / wb_total - 1, 4),
        sources=[
            dict(who='the district’s workbook states',
                 amount=round(wb_total, 2), level='stated',
                 what='its own printed Total Expenses across every sport',
                 table='athletics_by_sport'),
            dict(who='the revolving fund actually paid',
                 amount=round(fund_paid, 2), level='traced to a payment',
                 what='every disbursement in the fund’s cashbook that year',
                 table='fund_1301_cash_journal'),
            dict(who='the general fund carried',
                 amount=round(gf_total, 2), level='stated',
                 what='every athletics line in the district’s budget book',
                 table='athletics_history'),
        ])

    # ------------------------------- the reduction the minutes name, against the budget
    #
    # The minutes quote a figure. A quoted figure is a claim, so it is checked against the
    # district's own line rather than repeated: the last year middle school coaching was
    # funded, the budget carries exactly the amount the reduction is said to have removed.
    quotes = minutes_quotes()
    reduction_line = next(
        ((item, per_fy) for item, per_fy in items['general'].items()
         if item.lower() == MINUTES_REDUCTION_LINE.lower()), None)
    if reduction_line is None:
        fail(f'no general fund line called “{MINUTES_REDUCTION_LINE}” in '
             'athletics_history. The page checks a figure quoted from the minutes against '
             'that line, and a missing line is an unchecked quote.')
    red_item, red_by_fy = reduction_line
    red_fy = max(red_by_fy)
    reduction = dict(
        line=red_item, fy=red_fy, amount=round(red_by_fy[red_fy], 2),
        quoted=quotes[-1]['text'],
        matches=(f'${red_by_fy[red_fy]:,.0f}' in quotes[-1]['text']))
    if not reduction['matches']:
        fail(f'the minutes quote a reduction the budget line “{red_item}” does not match: '
             f'the line is {red_by_fy[red_fy]:,.2f} in FY{red_fy}. Either the quote or the '
             'line moved, and the page states that the two agree.')

    disclaimer = dict(
        board=MINUTES_BOARD, date=MINUTES_DATE, speaker=MINUTES_SPEAKER,
        doc=MINUTES_DOC, url=MINUTES_URL, town_url=MINUTES_TOWN_URL,
        quotes=quotes, reduction=reduction)

    # ------------------------------------------ where we differ from the prose, and why
    #
    # TWO OF THESE WERE RESOLVED on 7 September 2026 by correcting the analyses, and the
    # entries are gone rather than left standing as caveats: a page's job is to be current,
    # and a resolved disagreement is history. What replaces them is a CHECK, because the
    # thing that let them exist was that nothing compared the two.
    #
    # `verify_athletics.py` asserts the figures are present in the analyses. This asserts
    # the other direction -- that the SUPERSEDED figures are gone. Both are needed: a
    # document can carry the new number in one table and the old one in a sentence
    # underneath, which is exactly the shape of every defect in this project.
    for _doc, _gone, _what in (
        ('athletics.md', '314,319', 'the FY2024 general fund total'),
        ('athletics-ledger.md', '44%', 'the FY2024 share of workbook cost'),
        ('athletics-ledger.md', '65,073', 'FY2024 coaches on the general fund side'),
        ('athletics-ledger.md', '153,339', 'the FY2024 comparable general fund total'),
    ):
        _p = os.path.join(ROOT, 'sources', 'analyses', _doc)
        if _gone in open(_p, encoding='utf-8').read():
            fail(f'{_doc} still carries {_gone} for {_what}. That figure was superseded '
                 f'when commit 07aa298 withdrew three FY2024 rows. Either the correction '
                 f'was reverted or a second copy of it was missed.')

    recomputed = [
        dict(what='Whether the middle school blended fee exceeds its own top tier, FY2026',
             ours=None, published=None, boolean=True,
             where='athletics-ledger.md §8',
             why='That section reports the middle school half as unresolved, because no '
                 'document it held gave a 2025-26 middle school rate and the blended rate '
                 'therefore exceeded the only rate stated. The fee register now carries '
                 'one — $275, from School Committee minutes of 26 February 2025 — and '
                 'the blended rate recomputed below comes in under it, which is what a '
                 'blend of full pay, reduced fees and waivers has to do. On that figure '
                 'the anomaly does not arise.'),
    ]

    # The workbook's transportation total is the same quantity the two budget sides add
    # to, in both years it covers -- so it is a CHECK rather than a third series, and the
    # page can say the appropriation and the fund's share are two parts of one cost.
    for r in transport:
        wbt = metric_tot.get(r['fy'], {}).get('Transportation')
        r['cost'] = round(wbt, 2) if wbt is not None else None
        if wbt is not None and r['general'] is not None and r['fund'] is not None:
            if abs(r['general'] + r['fund'] - wbt) > CENT:
                fail(f'FY{r["fy"]}: the appropriation plus the fund’s share is '
                     f'{r["general"] + r["fund"]:,.2f} against the workbook’s '
                     f'transportation total of {wbt:,.2f} — they are no longer two parts '
                     'of one number, so the chart may not draw them as one')
        r['fund_share'] = (round(r['fund'] / wbt, 4)
                           if wbt and r['fund'] is not None else None)

    # Cost per participation. OURS, not the workbook's: it prints a cost and it prints a
    # headcount and it never divides one by the other. A participation is not a student --
    # one child in three seasons is three of these.
    for r in part_totals:
        t = printed.get(r['fy'])
        r['cost'] = round(t, 2) if t is not None else None
        r['per_participation'] = round(t / r['total'], 2) if t and r['total'] else None

    # WHAT A PARTICIPATION ACTUALLY PAID, in the one year both halves exist. The fund's
    # own year-end report gives NET user fees by level; the workbook gives participations
    # by level. Dividing is ours. Rule 11 twice over: the revenue is net of the payment
    # processor's cut, so this is what the fund banked and not what a family was charged,
    # and a blended rate must come in UNDER the top tier once waivers and sibling
    # discounts are in the pool -- which is the test.
    fee_check = []
    for lvl, item, label in (('HS', 'REVENUE — High school user fees (net)', 'High school'),
                             ('MS', 'REVENUE — Middle school user fees (net)', 'Middle school')):
        net = rev_items.get(item, {}).get(2026)
        n = next((r['hs'] if lvl == 'HS' else r['ms'])
                 for r in part_totals if r['fy'] == 2026)
        stated = next((f['amount'] for f in fees
                       if f['fy'] == 2026 and f['level'] == lvl and f['item'] == 'full_pay'),
                      None)
        if net is None or not n:
            fail(f'FY2026 {label}: no net user-fee row or no participations — the join '
                 'between the fund’s report and the workbook matched nothing')
        fee_check.append(dict(level=label, net=round(net, 2), participations=n,
                              per_participation=round(net / n, 2), stated_fee=stated,
                              under_top_tier=bool(stated and net / n < stated)))

    # ---------------------------------------------------------------- the gaps register
    gaps = q(c, 'SELECT side, what, why FROM money_gaps')
    keep = [g for g in gaps
            if any(w in (g['what'] + ' ' + g['why']).lower()
                   for w in ('athletic', 'revolving', 'special revenue fund',
                             'end of year financial report', 'play sports'))]
    if not keep:
        fail('no money_gaps row mentions athletics — rule 7c says a limit this page hits '
             'is registered there, and the join that reads them back matched nothing')

    # ----------------------------------------------------------------- the two analyses
    with open(REPORTS, encoding='utf-8') as fh:
        by_id = {r['id']: r for r in json.load(fh)['reports']}
    related = []
    for rid, why in RELATED:
        r = by_id.get(rid)
        if r is None:
            fail(f'reports.json no longer carries {rid}, which this page is built from')
        related.append(dict(id=rid, title=r['title'], why=why, words=r['words'],
                            updated=r['updated'], url=r['markdown']['url'],
                            pdf=(r.get('pdf') or {}).get('url')))

    # ------------------------------------------------------ WHAT THIS PAGE CONCLUDES
    #
    # Rule 8 governs: the job is helping a resident understand who pays for a season of
    # school sports and what each option costs somebody. Every figure below is one already
    # computed above, so a conclusion cannot state more than the payload holds.
    #
    # The latest year both pots are visible, chosen from the data rather than named, and
    # matched to the participation count for the same year -- a per-participation figure
    # built from two different years would be the like-for-like error in one division.
    paid_years = [r for r in both if r['all_in'] is not None]
    if not paid_years:
        fail('no year has both sides published, so nothing can be said about what a '
             'season takes out of the two pots together')
    latest = paid_years[-1]
    part_latest = next((r for r in part_totals if r['fy'] == latest['fy']), None)
    if part_latest is None or not part_latest['total']:
        fail(f'FY{latest["fy"]}: both sides are published and no participation count '
             'joins to it. A cost per participation with no denominator is not one.')
    per_participation = latest['all_in'] / part_latest['total']
    if not latest['revenue']:
        fail(f'FY{latest["fy"]}: no fee revenue row, so the share families put in cannot '
             'be computed and must not be described')
    family_share = 100.0 * latest['revenue'] / latest['all_in']
    hs = next(r for r in fee_check if r['level'] == 'High school')

    # The years the workbook's transportation total, the appropriation and the fund's
    # share are ALL published -- the only years the split between the two pots is visible.
    split = [r for r in transport
             if r['cost'] is not None and r['fund'] is not None and r['general'] is not None]
    if len(split) < 2:
        fail('fewer than two years carry all three transportation figures, so the '
             'sentence about the split moving has nothing to move between')
    t_from, t_to = split[0], split[-1]
    t_last = transport[-1]
    if t_last['general'] is None:
        fail('the most recent year carries no general fund transportation line, and the '
             'conclusion names it')

    # Of the difference between what left the two pots and what the workbook says the
    # whole programme cost, the part that is SCOPE -- general fund lines the workbook does
    # not carry at all -- and the part that is not accounted for by either document.
    scope = compare['unmatched_total']
    unexplained = three_way['over_workbook'] - scope

    # WHAT THE TOWN'S OWN ACCOUNTING SYSTEM CALLS ATHLETICS, and what it cannot split.
    # Computed last because it checks itself against `spend['general']`, which everything
    # above is built from.
    count = counted(c, spend['general'], items['general'], compare['unmatched'],
                    compare['unmatched_total'])
    equip = [r for r in count['accounts'] if r['name'] in EQUIPMENT_ACCOUNTS]
    if len(equip) != len(EQUIPMENT_ACCOUNTS):
        fail(f'FY{LEDGER_FY}: expected the equipment accounts {EQUIPMENT_ACCOUNTS} under '
             f'function {ATH_FUNCTION} and found {[r["name"] for r in equip]}. The page '
             'sets what they spent beside what a coach asked for, and it cannot do that '
             'against a line it did not find.')
    count['equipment'] = dict(
        accounts=equip,
        revised=round(sum(r['revised'] for r in equip), 2),
        expended=round(sum(r['expended'] for r in equip), 2),
        said=dict(board=MINUTES_BOARD, date=MINUTES_DATE, speaker=HELMETS_SPEAKER,
                  url=MINUTES_URL, town_url=MINUTES_TOWN_URL,
                  quotes=minutes_quotes(MINUTES_DOC, HELMETS_SPEAKER, HELMETS_QUOTES)))

    count['said'] = dict(
        board=FIELDS_BOARD, date=FIELDS_DATE, speaker=FIELDS_SPEAKER,
        url=FIELDS_URL, town_url=FIELDS_TOWN_URL,
        quotes=minutes_quotes(FIELDS_DOC, FIELDS_SPEAKER, FIELDS_QUOTES))

    # ---------------------------------------------- rule 15a, the archive searched
    #
    # WINDOW. This statement runs a page and a half of minutes, so the last quote sits
    # about four thousand characters after the speaker is named. The default window is
    # sized for a short public comment and would reject it; widening it here, at the call,
    # with the reason, keeps the check meaningful everywhere else.
    by_sport_said = dict(
        board=MINUTES_BOARD, date=MINUTES_DATE, speaker=BYSPORT_SPEAKER,
        url=MINUTES_URL, town_url=MINUTES_TOWN_URL,
        quotes=minutes_quotes(MINUTES_DOC, BYSPORT_SPEAKER, BYSPORT_QUOTES, window=5000))
    helmets_sequel = dict(
        board=MINUTES_BOARD, date=AGENDA_DATE, kind='agenda',
        url=AGENDA_URL, town_url=AGENDA_TOWN_URL,
        quotes=minutes_quotes(AGENDA_DOC, False, AGENDA_QUOTES))
    search_terms, minutes_cov = searched()

    # RULE 2 APPLIED TO THE GAP REGISTER, which is prose that ships.
    #
    # `money-gaps.csv` is written by hand -- it is read by the API, by the records request
    # and by /what-we-cannot-answer as well as by this page -- so the figures inside it are
    # exactly the thing rule 2 warns about: typed, checkable by nothing, and rendering
    # confidently long after the model has moved. The row about the buildings states the
    # two totals this block computes, so they are asserted against it here. A gap whose own
    # arithmetic has gone stale is worse than no gap: it is a records request for the wrong
    # document.
    facility_gap = next((g for g in gaps
                         if 'grounds, custodial' in g['what'].lower()), None)
    if facility_gap is None:
        fail('money-gaps.csv no longer registers the grounds and custodial share. Rule 7c: '
             'a limit this page states has to be a row there, because the page is not what '
             'the records request reads.')
    for _what, _text in (('the athletics appropriation', f'${count["appropriated"]:,.0f}'),
                         ('the facility total', f'${count["facility_total"]:,.0f}'),
                         ('the account count', f'{len(count["accounts"])} accounts')):
        if _text not in facility_gap['why']:
            fail(f'the buildings gap in money-gaps.csv no longer states {_text} for '
                 f'{_what}. The register is what the request letter and the API read, so '
                 'a figure that has drifted there is a figure this project is publishing '
                 'wrong in three places.')
    # The two accounts a reader asks about by name. Looked up rather than indexed, and
    # the build stops if either stops being there: a conclusion naming the athletic
    # director is a conclusion that has to have found the athletic director.
    def ledger_account(name):
        hit = [r for r in count['accounts'] if r['name'] == name]
        if len(hit) != 1:
            fail(f'FY{LEDGER_FY}: {len(hit)} accounts named {name!r} under function '
                 f'{ATH_FUNCTION}. A conclusion names that line, and a name that resolves '
                 'to none or to several is not a citation.')
        return hit[0]

    ad_line = ledger_account('ADSALARY')
    trainer_line = ledger_account('ATHTRAINER')

    return dict(
        generated_by='scripts/build_athletics_charts.py',
        source='sources/data/lunenburg.db — athletics_history, athletics_by_sport, '
               'athletic_fee_schedule, fund_1301_cash_journal, money_gaps',
        coverage=dict(
            history_years=years,
            cost_years=cost_years, part_years=part_years, mix_years=mix_years,
            fund_years=[r['fy'] for r in flow],
            postings=len(j), sports=len({(k[0], k[1], k[2]) for k in ath}),
            fee_rows=len(fees),
            disbursements=len(disb), disbursements_named=len(named)),
        both_sides=both,
        transport=transport,
        coaching=coaching,
        categories=categories,
        category_order=CAT_ORDER,
        by_sport=by_sport,
        participation=participation,
        participation_totals=part_totals,
        negatives=negatives,
        fee_mix=mix, count_columns=COUNT_COLUMNS,
        fees=fees, fee_headline=headline,
        fund_flow=flow, fund_sources=src_rows,
        memo_entries=memo, memo_total=memo_total,
        compare=compare,
        counted=count,
        three_way=three_way,
        disclaimer=disclaimer,
        attribution=attribution,
        fee_check=fee_check,
        fy26_fund=dict(
            revenue=next(r['revenue'] for r in both if r['fy'] == 2026),
            spending=next(r['revolving'] for r in both if r['fy'] == 2026),
            appropriation=next(r['general'] for r in both if r['fy'] == 2026),
            all_in=next(r['all_in'] for r in both if r['fy'] == 2026)),
        by_sport_said=by_sport_said,
        helmets_sequel=helmets_sequel,
        searched=search_terms,
        minutes=minutes_cov,
        recomputed=recomputed,
        gaps=[dict(side=g['side'], what=g['what'], why=g['why']) for g in keep],
        related=related,
        # ---- WHAT A READER CAN DO WITH EACH OF THESE, argued rather than assigned ----
        #
        # `bearing` was set on these three in one pass and then re-examined, because an
        # axis applied by reflex is the same as no axis. The argument, one conclusion at a
        # time:
        #
        #   `more-left-the-accounts-than-any-document-totals` -- SIZES. It establishes how
        #   big the programme actually was and that no published document totals it.
        #   Nothing in it is a dial: a resident cannot vote on the spread between three
        #   documents, and the remedy -- ask for the accounts-payable detail -- is a
        #   request for a MEASUREMENT rather than a decision with a cost. Rule 8's test is
        #   what each option costs somebody, and this option costs nobody anything.
        #
        #   `everything-the-books-call-athletics-and-what-they-cannot` -- SIZES, and it is
        #   the clearest case of the three. It draws the box: what the ledger codes to
        #   athletics, and the buildings that no programme code touches. A box is context
        #   by construction. You cannot act on a problem you have not sized.
        #
        #   `the-bus-bill-fell-and-the-town-paid-more` -- LEVER, and this is the one worth
        #   arguing. The temptation is to call it `sizes` too, because the page cannot say
        #   WHY the split moved and says so. But `bearing` is not about whether the cause
        #   is known; it is about whether a body in this town has a dial. It does: which
        #   pot pays a given athletics cost is settable -- the School Committee sets the
        #   fee and what the revolving fund carries, Town Meeting votes the appropriation
        #   -- and this conclusion is the archive watching that dial being turned, with
        #   the cost of the thing itself falling while the town's share more than doubled.
        #   Rule 8 holds: it names the dial and what moving it did, and it does not say
        #   which way anybody should set it.
        conclusions=emit('what-sports-cost', [
            conclusion(
                id='more-left-the-accounts-than-any-document-totals',
                bearing='sizes',
                claim='Left the town’s accounts for athletics in %s, more than any '
                      'document totals' % C.fy(three_way['fy']),
                so_what='The district’s own workbook puts the whole programme well below that. The spread is published, not reconciled.',
                lede='Athletics took %s out of the town\u2019s two pots in %s '
                      '\u2014 %s more than the district\u2019s own workbook says the '
                      'whole programme cost.'
                      % (C.usd(three_way['two_pots']), C.fy(three_way['fy']),
                         C.usd(three_way['over_workbook'])),
                detail='%s of it is traced to individual payments in the fee-funded '
                       'fund\u2019s cashbook \u2014 the only transaction-level record of '
                       'athletics in this archive \u2014 and %s is the appropriation in '
                       'the district\u2019s budget book. Part of the difference is '
                       'scope: %s of the appropriation sits on lines like the athletic '
                       'director and the trainer that the workbook does not carry at all. '
                       'That leaves %s neither document accounts for. Every per-sport '
                       'figure anybody quotes comes from that one workbook, so the spread '
                       'is published rather than reconciled \u2014 averaging figures '
                       'different people assembled to answer different questions would be '
                       'adding a claim the documents do not make.'
                       % (C.usd(three_way['fund_paid']), C.usd(three_way['general']),
                          C.usd(scope), C.usd(unexplained)),
                figures={
                    'two_pots': figure(three_way['two_pots'],
                                       C.usd(three_way['two_pots'])),
                    'fy': figure(three_way['fy'], C.fy(three_way['fy'])),
                    'over_workbook': figure(three_way['over_workbook'],
                                            C.usd(three_way['over_workbook'])),
                    'fund_paid': figure(three_way['fund_paid'],
                                        C.usd(three_way['fund_paid'])),
                    'general': figure(three_way['general'], C.usd(three_way['general'])),
                    'scope': figure(scope, C.usd(scope)),
                    'unexplained': figure(unexplained, C.usd(unexplained)),
                },
                figure='two_pots',
                kind='measured',
                basis='Three documents for one year. The fund\u2019s payments come out of '
                      'fund_1301_cash_journal \u2014 the town\u2019s accounting system, '
                      'every disbursement, and it chains to the town\u2019s own printed '
                      'opening balance in each following year. The other two are figures '
                      'people assembled: athletics_by_sport is the district\u2019s '
                      'by-sport workbook and its own printed Total Expenses, and '
                      'athletics_history is the budget book. However official a sheet '
                      'looks, a figure somebody typed is stated and a figure the '
                      'accounting system printed is evidence.',
                not_shown='Which figure is right, or what any one sport cost. Two of the '
                          'three are totals somebody assembled and only the fund\u2019s '
                          'payments are traced to a payment \u2014 and even those cannot '
                          'be put against a sport: not one disbursement in the cashbook '
                          'names a sport anywhere on the row. The accounts-payable detail '
                          'behind the warrants is what would close it.',
                see=[('/sources', 'what produced each document\u2019s figures'),
                     ('/what-we-cannot-answer', 'what the record cannot answer')],
            ),
            conclusion(
                id='everything-the-books-call-athletics-and-what-they-cannot',
                bearing='sizes',
                claim='Everything the town’s books code to athletics in %s — director '
                      'and trainer included' % C.fy(count['fy']),
                so_what='Not the buildings. Grounds, heat and custodians split by no programme, so this is a floor.',
                lede='The town\u2019s accounting system codes %d accounts to function '
                     '%s, Athletics, in %s \u2014 %s appropriated, and the '
                     'district\u2019s budget book states the same total to the cent.'
                     % (len(count['accounts']), count['function'], C.fy(count['fy']),
                        C.usd(count['appropriated'])),
                detail='Inside it are the athletic director at %s, the trainer at %s, the '
                       'secretary, the police details and the insurance \u2014 and the '
                       'district\u2019s own sport-by-sport workbook carries none of the '
                       'first four. In %s, the one year the two can be set side by side, '
                       'that was %s of appropriation the per-sport '
                       'figures never saw, which is a large part of why the published '
                       'totals disagree. Outside it are the buildings: custodians, '
                       'heating, utilities, grounds and building maintenance are their '
                       'own functions in the same printout, %s across the whole school '
                       'department, and not one of those accounts carries the athletics '
                       'programme code. The pitch is still mown and the gym is still lit, '
                       'so what athletics costs is that %s plus a share of the %s that '
                       'nobody publishes.'
                       % (C.usd(ad_line['appropriated']), C.usd(trainer_line['appropriated']),
                          C.fy(count['workbook_fy']), C.usd(count['not_in_workbook_total']),
                          C.usd(count['facility_total']), C.usd(count['appropriated']),
                          C.usd(count['facility_total'])),
                figures={
                    'accounts': figure(len(count['accounts']), str(len(count['accounts']))),
                    'function': figure(count['function'], count['function']),
                    'fy': figure(count['fy'], C.fy(count['fy'])),
                    'appropriated': figure(count['appropriated'],
                                           C.usd(count['appropriated'])),
                    'director': figure(ad_line['appropriated'],
                                       C.usd(ad_line['appropriated'])),
                    'trainer': figure(trainer_line['appropriated'],
                                      C.usd(trainer_line['appropriated'])),
                    'workbook_fy': figure(count['workbook_fy'],
                                          C.fy(count['workbook_fy'])),
                    'not_in_workbook': figure(count['not_in_workbook_total'],
                                              C.usd(count['not_in_workbook_total'])),
                    'facility': figure(count['facility_total'],
                                       C.usd(count['facility_total'])),
                },
                figure='appropriated',
                kind='measured',
                basis='The town\u2019s own MUNIS year-to-date budget report for '
                      'FY%d period %s \u2014 a printout of what the books say, with '
                      'account numbers, transfers and a total the system foots itself. '
                      'Function %s is Athletics in the town\u2019s chart of accounts and '
                      'in DESE\u2019s, so the ledger and the state name the same box. The '
                      'build refuses to publish this if the ledger and the district\u2019s '
                      'budget book stop agreeing on the total, or if a grounds or '
                      'custodial account ever does carry the athletics programme code.'
                      % (count['fy'], count['period'], count['function']),
                not_shown='What athletics costs. This is what the town APPROPRIATES for '
                          'it, which is rule 11: net of the fee-funded fund, net of any '
                          'grant, and with no share of the buildings in it at all. Nor '
                          'does an account name a person or a post \u2014 a line called '
                          'ATHTRAINER is dollars, not a trainer, and the town publishes no '
                          'FTE against it.',
                see=[('/what-we-cannot-answer', 'the grounds share nobody publishes'),
                     ('/connecting-the-budget', 'how a budget line reaches the ledger')],
            ),
            conclusion(
                id='the-bus-bill-fell-and-the-town-paid-more',
                bearing='lever',
                claim='Budgeted for athletic buses in %s, more than double the year '
                      'before' % C.fy(t_to['fy']),
                so_what='The bus bill itself fell that year. What changed is which pot paid, not what it cost.',
                lede='Lunenburg\u2019s athletic transportation line rose from %s to %s '
                      'in a year when the bus bill itself fell from %s to %s: the cost '
                      'went down and the town\u2019s share went up.'
                      % (C.usd(t_from['general']), C.usd(t_to['general']),
                         C.usd(t_from['cost']), C.usd(t_to['cost'])),
                detail='In %s the fee-funded fund paid %s of that bill, %s of it; in %s '
                       'it paid %s, %s. Nothing about the buses had to change for the '
                       'town\u2019s line to more than double \u2014 what changed is '
                       'which pot paid. The two sides sum to the district\u2019s own '
                       'transportation total exactly in both years, which is what lets '
                       'them be read as two parts of one bill, and the %s line is %s. It '
                       'is the clearest measurement on this site of why a budget line '
                       'rising is not a cost rising.'
                       % (C.fy(t_from['fy']), C.usd(t_from['fund']),
                          C.pct(t_from['fund_share'] * 100), C.fy(t_to['fy']),
                          C.usd(t_to['fund']), C.pct(t_to['fund_share'] * 100),
                          C.fy(t_last['fy']), C.usd(t_last['general'])),
                figures={
                    'general_from': figure(t_from['general'], C.usd(t_from['general'])),
                    'general_to': figure(t_to['general'], C.usd(t_to['general'])),
                    'cost_from': figure(t_from['cost'], C.usd(t_from['cost'])),
                    'cost_to': figure(t_to['cost'], C.usd(t_to['cost'])),
                    'fy_from': figure(t_from['fy'], C.fy(t_from['fy'])),
                    'fy_to': figure(t_to['fy'], C.fy(t_to['fy'])),
                    'fund_from': figure(t_from['fund'], C.usd(t_from['fund'])),
                    'fund_to': figure(t_to['fund'], C.usd(t_to['fund'])),
                    'share_from': figure(t_from['fund_share'] * 100,
                                         C.pct(t_from['fund_share'] * 100)),
                    'share_to': figure(t_to['fund_share'] * 100,
                                       C.pct(t_to['fund_share'] * 100)),
                    'latest_fy': figure(t_last['fy'], C.fy(t_last['fy'])),
                    'latest_general': figure(t_last['general'],
                                             C.usd(t_last['general'])),
                },
                figure='general_to',
                kind='measured',
                basis='athletics_history, both sides, checked on every build against '
                      'athletics_by_sport\u2019s own transportation total \u2014 the '
                      'appropriation and the fund\u2019s share sum to the '
                      'workbook\u2019s figure to the cent in both years, and the build '
                      'refuses to draw them as two parts of one bill if they stop doing '
                      'so.',
                not_shown='Why the split moved. A fund carrying two thirds of a bill in '
                          'one year and almost none of it the next fits a deliberate '
                          'decision, a fund that could not afford it, and a change in '
                          'which fund the charge was coded to, equally well; no document '
                          'here says which. The fund\u2019s own year-end report for '
                          'those years, or the warrant detail behind the payments, is '
                          'what would settle it.',
                see=[('/money-outside-the-budget', 'the funds outside the budget'),
                     ('/find-the-money', 'where the money is')],
            ),
        ]),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {rel} is not what the database now produces. '
                  'Run scripts/build_athletics_charts.py.')
            return 1
        print(f'ok — {rel} reproduces from the database')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    print(f'wrote {rel} — {len(d["both_sides"])} years of both sides, '
          f'{d["coverage"]["postings"]} postings, {d["coverage"]["sports"]} sports, '
          f'FY{d["compare"]["fy"] % 100} appropriation covers '
          f'{d["compare"]["share"] * 100:.0f}% of the workbook’s cost')
    return 0


if __name__ == '__main__':
    sys.exit(main())
