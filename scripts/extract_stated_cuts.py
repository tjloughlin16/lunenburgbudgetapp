#!/usr/bin/env python3
"""Every reduction and restoration the district PUT IN WRITING, read off its own pages.

    python3 scripts/extract_stated_cuts.py           # write sources/data/stated-cuts.csv
    python3 scripts/extract_stated_cuts.py --check   # fail if it no longer reproduces

WHAT THIS IS, AND THE ONE THING IT IS NOT. A reduction list is a document somebody
ASSEMBLED to make an argument for a budget. Rule 13a: that makes every row here `stated`,
however official the slide looks. It is evidence of what the district said it intended to
do, published by the district, in the district's own words -- and it is not evidence that
anything happened. Whether an instrument later saw the change is a different question,
asked in scripts/build_cut_register.py against data nobody in this argument produced.

NOTHING IN THE `printed` COLUMN IS TYPED HERE. Rule 13: quote the source, never your
rendering of it. Every row's `printed` string is read out of the extracted text at a
stated page, and `position`, `school`, `fte` and `amount` are derived from that string by
rules in this file. So the register can be checked one row at a time against the document,
and a change to the extraction fails this script rather than silently rewriting history.

EACH BLOCK ASSERTS ITS OWN ROW COUNT. A parser that matches nothing looks exactly like a
document with no cuts in it -- the shape of four of the thirteen defects found here on
5 September 2026. Every block below states how many rows it must find and this refuses to
write if it finds a different number.

THREE READINGS THAT ARE OURS, and they are declared rather than hidden:

  1. THE FY25 ESSER SLIDE IS TWO COLUMNS AND THE EXTRACTOR INTERLEAVED THEM. Page 43 of
     `fy25-superintendent-39-s-budget-update` prints twelve positions under one caption
     and ten under another; in the text layer both captions land BELOW their own column.
     We take the ten lines between the second caption and the page break. An instrument
     that reformats before you see it is part of the finding.
  2. THE SCHOOL IS READ FROM WHAT THE PAGE PRINTS, never inferred from a job title. Where
     the document prints no school the row says `not stated`.
  3. AN FTE OR A DOLLAR FIGURE IS ONLY RECORDED WHERE THE DOCUMENT PRINTS ONE. The FY26
     approved list prints neither for most of its 39 rows and the register leaves both
     empty rather than sourcing them from a neighbouring document.

WHAT `conditional_on` IS FOR. In FY25 the School Committee published TWO lists -- cuts
without an override and cuts with one -- and the override passed. A register that flattened
those into one list would state as cut nine things the town voted to keep.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources/data/stated-cuts.csv')
TEXT = os.path.join(ROOT, 'sources')
MANIFEST = os.path.join(ROOT, 'sources/data/archive-manifest.csv')

FIELDS = ['fy', 'doc_date', 'doc_title', 'stage', 'block', 'direction', 'conditional_on',
          'printed', 'position', 'school', 'school_printed', 'fte', 'amount',
          'consequence', 'page', 'doc_text', 'doc_pdf', 'sha256', 'basis']

# The schools, as the documents spell them. The key is ours; every spelling in the value
# is one the district actually printed, and `school_printed` keeps what the page said.
SCHOOLS = [
    ('primary', ['lunenburg primary school', 'primary school', 'primary', 'lps', 'ps',
                 'p.s.']),
    ('turkey-hill', ['turkey hill elementary school', 'turkey hill elementary',
                     'turkey hill', 'thes']),
    ('middle', ['lunenburg middle school', 'middle school', 'lms']),
    ('high', ['lunenburg high school', 'lunenburg high', 'high school', 'lhs']),
    ('mid-high', ['lmhs', 'lhs/lms', 'lms/lhs', 'lhms']),
    ('ace', ['ace']),
    ('district', ['districtwide', 'district wide', 'district', 'all buildings',
                  'central office']),
    ('athletics', ['athletics', 'athletic department']),
    # The documents write a shared post with a slash, and both halves are real. A row
    # filed under one of them would say the district cut something at a school it did
    # not name alone.
    ('primary-and-turkey-hill', ['ps/thes', 'thes/ps',
                                 'primary/turkey hill elementary',
                                 'primary/turkey hill']),
    ('high-and-primary', ['lhs/primary']),
    ('middle-and-high', ['ms/hs']),
]
SCHOOL_KEY = {sp: key for key, spellings in SCHOOLS for sp in spellings}

# A leading bullet is the EXTRACTOR'S rendering, not the district's text: PDF decks in
# this archive carry Wingdings bullets that land in the text layer as private-use
# characters (U+F0D8, U+F084). They are stripped from the front of a printed line and
# from nowhere else, so what the register quotes stays a substring of the document.
BULLET_RE = re.compile(r'^[\s\u2022\u25cb\u25cf\u25aa\u00b7*\-\u2013\u2014'
                       r'\uf000-\uf0ff]+')


def debullet(s):
    return BULLET_RE.sub('', s).strip()


FTE_RE = re.compile(r'(?<![\d.])(\d+(?:\.\d+)?|\.\d+)\s*FTE', re.I)
PAREN_FTE_RE = re.compile(r'\((?:reduce[d]?\s*)?(\d*\.\d+)\)')
# `$205,019 2.0 Classroom FTE at Primary`, `$  .2 Music teacher at Turkey Hill`. The FY27
# documents lead with the money and then the FTE, and half of those FTEs are written
# without the letters. A DECIMAL POINT is required, so a whole number leading a line --
# `1 Interventionist`, or a count of posts -- is never read as an FTE.
LEAD_FTE_RE = re.compile(r'^\s*(\d*\.\d+)\s+[A-Za-z]')
USD_RE = re.compile(r'\$\s?([\d,]+(?:\.\d\d)?)')


def fail(msg):
    sys.exit('REFUSING TO WRITE — %s' % msg)


def pages(rel):
    """The extracted text, split into the pages the extractor marked.

    Returns {page_number: [line, ...]}. Refuses on a file with no page markers, because
    every citation in this register is a page coordinate and a register that cannot give
    one is not checkable."""
    path = os.path.join(TEXT, rel)
    if not os.path.exists(path):
        fail('%s is not here — run scripts/sync_archive.py --pull' % rel)
    body = open(path, encoding='utf-8', errors='replace').read()
    out, cur = {}, None
    for line in body.splitlines():
        m = re.match(r'^===PAGE (\d+)===\s*$', line)
        if m:
            cur = int(m.group(1))
            out[cur] = []
            continue
        if cur is None:
            cur = 1
            out.setdefault(1, [])
        out[cur].append(line.rstrip())
    if not out:
        fail('%s carries no ===PAGE=== markers, so nothing here can cite a page' % rel)
    return out


def flat(rel):
    """The whole document as one page, for the few sources the extractor left unpaged."""
    path = os.path.join(TEXT, rel)
    if not os.path.exists(path):
        fail('%s is not here' % rel)
    return {1: [l.rstrip() for l in
                open(path, encoding='utf-8', errors='replace').read().splitlines()]}


def school_of(text):
    """The school a printed string names, or ('not stated', '').

    Longest spelling first, so `Lunenburg Primary School` is taken before `Primary`, and
    matched on word boundaries so `PS` does not fire inside `MAPS`."""
    low = ' %s ' % re.sub(r'[^a-z0-9./ ]+', ' ', text.lower())
    low = re.sub(r'\s+', ' ', low)
    for sp in sorted(SCHOOL_KEY, key=len, reverse=True):
        if re.search(r'(?<![a-z0-9])%s(?![a-z0-9])' % re.escape(sp), low):
            return SCHOOL_KEY[sp], sp
    return 'not stated', ''


def fte_of(text):
    """The FTE the string PRINTS, or ''. Two shapes appear: `1.0FTE` / `2.0 Classroom
    FTE`, and a bare decimal in brackets as the FY26 approved list writes it — `(.25)`,
    `(reduced 0.2)`. A whole number in brackets is a COUNT of posts, not an FTE
    (`Paraprofessional (3) LHS`), and is deliberately not read as one."""
    m = FTE_RE.search(text)
    if m:
        return '%g' % float(m.group(1))
    m = PAREN_FTE_RE.search(text)
    if m:
        return '%g' % float(m.group(1))
    m = LEAD_FTE_RE.match(USD_RE.sub(' ', text).replace('$', ' ').lstrip())
    if m:
        return '%g' % float(m.group(1))
    return ''


def amount_of(text):
    m = USD_RE.search(text)
    if not m:
        return ''
    return '%.2f' % float(m.group(1).replace(',', ''))


def position_of(printed):
    """What the row is about, with the school words, the money and the FTE taken out.

    Ours, and derived rather than typed — `printed` is what a reader should quote."""
    s = printed
    s = USD_RE.sub(' ', s)
    s = re.sub(r'\(\s*\)', ' ', s)
    s = re.sub(r'^\s*[-•○●▪*]+\s*', '', s)
    s = re.sub(r'\s+', ' ', s).strip(' -–—:*')
    return s


def sha_index():
    if not os.path.exists(MANIFEST):
        fail('sources/data/archive-manifest.csv is not here — rule 12 says every source '
             'carries its hash, and this register will not publish one without it')
    out = {}
    for r in csv.DictReader(open(MANIFEST, encoding='utf-8')):
        out[r['key']] = r['sha256']
    return out


# ---------------------------------------------------------------- the blocks
#
# One entry per list the district printed. `expect` is not decoration: a parser that
# matches nothing and a document with no cuts in it are the same output, and this is the
# assertion that separates them.

def block_lines(pg, page, start=None, stop=None, expect=None, rel='', **kw):
    """The lines of one page between two anchors, both matched VERBATIM.

    `start` and `stop` are strings the page must contain, in that order. The anchors are
    quoted out of the document itself, so an extractor change breaks this rather than
    quietly shifting which lines are read."""
    if page not in pg:
        fail('%s has no page %d' % (rel, page))
    lines = pg[page]
    i, j = 0, len(lines)
    if start is not None:
        hit = [k for k, l in enumerate(lines) if start in l]
        if not hit:
            fail('%s page %d no longer contains %r — the anchor this block is read from '
                 'has moved' % (rel, page, start))
        i = hit[0] + 1
    if stop is not None:
        hit = [k for k, l in enumerate(lines) if k >= i and stop in l]
        if not hit:
            fail('%s page %d no longer contains %r after %r'
                 % (rel, page, stop, start))
        j = hit[0]
    out = [l.strip() for l in lines[i:j] if l.strip()]
    if kw.get('bulleted'):
        # A slide's bullet wraps. A line that does not open with the bullet character the
        # page uses is the tail of the one above it, and joining them is how the register
        # ends up quoting the district's whole sentence rather than half of it.
        joined = []
        for s in out:
            if re.match(r'^[•○●▪\-–—*]\s*', s) or not joined:
                joined.append(s)
            else:
                joined[-1] = joined[-1] + ' ' + s
        out = joined
    out = [l for l in (debullet(x) for x in out) if l]
    if expect is not None and len(out) != expect:
        fail('%s page %d: expected %d printed lines between the anchors and read %d — '
             '%r' % (rel, page, expect, len(out), out))
    return out


def rows_from(rel, page, lines, **kw):
    out = []
    forced = kw.get('school')
    for printed in lines:
        key, printed_school = school_of(printed)
        out.append(dict(
            printed=printed, position=position_of(printed),
            school=forced or key,
            school_printed=kw.get('school_printed', printed_school),
            fte=fte_of(printed), amount=amount_of(printed),
            page=page, doc_text=rel, basis='stated'))
    return out


DOCS = {}


def doc(key, fy, date, title, stage, text, pdf):
    DOCS[key] = dict(fy=fy, doc_date=date, doc_title=title, stage=stage,
                     text=text, pdf=pdf)
    return key


D = 'district-budget/'
FY20_FEB = doc('fy20-feb', 2020, '2019-02-06',
               'FY20 Budget Update — Recommended Reductions as of February 6, 2019',
               'gap identified',
               D + 'text/fy20-budget-update-recommended-reductions-as-of-february-6-2019.txt',
               D + 'docs/fy20-budget-update-recommended-reductions-as-of-february-6-2019.pdf')
FY20_MAR = doc('fy20-mar', 2020, '2019-03-06',
               'FY20 Budget Update — Recommended Reductions as of March 6, 2019',
               'reductions recommended',
               D + 'text/fy20-budget-update-recommended-reductions-as-of-march-6-2019.txt',
               D + 'docs/fy20-budget-update-recommended-reductions-as-of-march-6-2019.pdf')
FY20_MEMO = doc('fy20-memo', 2020, '2019-03-29',
                'Superintendent’s Budget Recommendations, March 29, 2019',
                'reductions recommended, and two restored',
                D + 'text/superintendent-s-budget-recommendations.txt',
                D + 'docs/superintendent-s-budget-recommendations.docx')
FY20_FINAL = doc('fy20-final', 2020, '2019-04-03',
                 'Superintendent’s Recommended FY20 Budget, budget hearing 3 April 2019',
                 'recommended budget as presented for adoption',
                 D + 'text/superintendent-s-recommended-fy20-budget-presentation.txt',
                 D + 'docs/superintendent-s-recommended-fy20-budget-presentation.pdf')
FY21 = doc('fy21', 2021, '2020-01-22',
           'Superintendent’s Proposed FY21 Budget Presentation, 22 January 2020',
           'reductions contemplated to reach the target',
           D + 'text/superintendent-s-proposed-fy21-budget-presentation.txt',
           D + 'docs/superintendent-s-proposed-fy21-budget-presentation.pdf')
FY25_OVR = doc('fy25-override', 2025, '2024-04',
               'Lunenburg School Committee Override Statement',
               'two lists, one conditional on a ballot question',
               D + 'text/lunenburg-school-committee-override-statement.txt',
               D + 'docs/lunenburg-school-committee-override-statement.pdf')
FY25_UPD = doc('fy25-update', 2025, '2024-03-21',
               'FY25 Superintendent’s Budget Update',
               'reductions recommended, with the district’s stated impact',
               D + 'text/fy25-superintendent-39-s-budget-update.txt',
               D + 'docs/fy25-superintendent-39-s-budget-update.pdf')
FY26 = doc('fy26', 2026, '2025-03-12',
           'School Committee Approved FY26 Budget — Personnel Cuts',
           'approved by the School Committee',
           D + 'text/school-committee-approved-fy26-budget-personnel-cuts.txt',
           D + 'docs/school-committee-approved-fy26-budget-personnel-cuts.pdf')
FY27_ADD = doc('fy27-addendum', 2027, '2026-03-13',
               'Budget Addendum: Multi-Scenario Financial Analysis, prepared 13 March 2026',
               'four scenarios, one of them the no-override budget',
               D + 'text/budget-addendum-multi-scenario-financial-analysis.txt',
               D + 'docs/budget-addendum-multi-scenario-financial-analysis.pdf')
FY27_SLIDES = doc('fy27-slides', 2027, '2026-03-23',
                  'Balanced Budget slides, School Committee, 23 March 2026',
                  'the no-override budget as voted',
                  D + 'text/balanced-budget-slides-3-23-26.txt',
                  D + 'docs/balanced-budget-slides-3-23-26.pdf')


# ---- FY2020 -----------------------------------------------------------------------

def fy20_march():
    rel = DOCS[FY20_MAR]['text']
    pg = pages(rel)
    out = []
    # Pages 4-7 each carry one school's block under the heading `Recommended Reductions`.
    # Page 4 is districtwide and prints three measures with no position attached to them.
    out += rows_from(rel, 4, block_lines(
        pg, 4, start='Districtwide', stop='Recommended Reductions', expect=3, rel=rel,
        bulleted=True),
        school='district', school_printed='Districtwide')
    # Pages 5-7 print `School name` then, per position, `Position: consequence` in one
    # paragraph. The colon is the district's own separator between the two.
    for page, headings in ((5, ['Lunenburg Primary School', 'Turkey Hill Elementary School']),
                           (6, ['Lunenburg Middle School']),
                           (7, ['Lunenburg High School'])):
        out += _colon_block(rel, pg, page, headings)
    if len(out) != 11:
        fail('the FY20 March 6 list read %d rows, not 11' % len(out))
    return out


def _colon_block(rel, pg, page, headings):
    """A slide printing `School`, then paragraphs of `Position: consequence`.

    The position is the text before the first colon on a line that starts one; every
    following line up to the next position or heading is the consequence."""
    lines = [l.rstrip() for l in pg[page]]
    school, school_printed = 'not stated', ''
    out, cur = [], None
    for raw in lines:
        s = raw.strip()
        if not s or s == 'Recommended Reductions':
            continue
        if s in headings:
            school_printed = s
            school = SCHOOL_KEY[s.lower()]
            cur = None
            continue
        body = re.sub(r'^\s*[•\-–—*]\s*', '', s)
        m = re.match(r'^([^:]{3,80}):\s*(.*)$', body)
        if m and school != 'not stated':
            cur = dict(printed=m.group(1).strip(), position=position_of(m.group(1)),
                       school=school, school_printed=school_printed,
                       fte=fte_of(m.group(1)), amount=amount_of(m.group(1)),
                       consequence=m.group(2).strip(), page=page, doc_text=rel,
                       basis='stated')
            out.append(cur)
        elif cur is not None:
            cur['consequence'] = (cur['consequence'] + ' ' + body).strip()
    for r in out:
        r['consequence'] = re.sub(r'\s+', ' ', r['consequence']).strip()
    if not out:
        fail('%s page %d produced no `Position: consequence` rows' % (rel, page))
    return out


def fy20_memo():
    rel = DOCS[FY20_MEMO]['text']
    pg = flat(rel)
    lines = [l.strip() for l in pg[1] if l.strip()]
    try:
        i = next(k for k, l in enumerate(lines)
                 if 'The following cuts are recommended:' in l)
        j = next(k for k, l in enumerate(lines)
                 if l.startswith('These recommended cuts will be presented'))
    except (ValueError, StopIteration):
        fail('the March 29 memo no longer carries the two anchors this block is read '
             'between')
    out, school, school_printed = [], 'not stated', ''
    for s in lines[i + 1:j]:
        key = SCHOOL_KEY.get(s.lower())
        if key and len(s) <= 12:
            school, school_printed = key, s
            continue
        out.append(dict(printed=s, position=position_of(s), school=school,
                        school_printed=school_printed, fte=fte_of(s),
                        amount=amount_of(s), page=1, doc_text=rel, basis='stated'))
    if len(out) != 9:
        fail('the March 29 memo read %d recommended cuts, not 9' % len(out))
    # The restoration sentence, taken whole. Two positions in one sentence, and the
    # register keeps the sentence as `printed` on both rows rather than paraphrasing it.
    sent = next((l for l in lines if l.startswith('The Leadership Team is recommending')),
                None)
    if sent is None or 'restore one foreign language teacher position to LHS' not in sent:
        fail('the March 29 memo no longer carries the restoration sentence this register '
             'quotes')
    restored = [
        ('one foreign language teacher position to LHS', 'high', 'LHS'),
        ('a 0.5 librarian position to the Primary School', 'primary', 'Primary School'),
    ]
    for frag, key, printed_school in restored:
        if frag not in sent:
            fail('the restoration sentence no longer names %r' % frag)
        out.append(dict(printed=frag, position=position_of(frag), school=key,
                        school_printed=printed_school, fte=fte_of(frag),
                        amount='', page=1, doc_text=rel, basis='stated',
                        direction='restoration',
                        consequence=sent[sent.index('This will allow'):]
                        if 'This will allow' in sent else ''))
    return out


def fy20_final():
    """Page 23 of the 3 April hearing deck: the final recommended budget's two columns.

    The extractor prints both columns as one run of lines and then the column HEADINGS
    below them — `New Positions Reduced Positions`. So the split is by content, not by
    layout, and it is done here on the district's own five reduced-position lines, which
    are the tail of the run. The count is asserted both ways."""
    rel = DOCS[FY20_FINAL]['text']
    pg = pages(rel)
    lines = block_lines(pg, 23, start=None, stop='New Positions Reduced Positions',
                        rel=rel)
    if len(lines) != 13:
        fail('page 23 of the FY20 hearing deck read %d position lines, not 13' % len(lines))
    reduced = lines[8:]
    if len(reduced) != 5 or not reduced[0].startswith('LMS FL Teacher'):
        fail('the reduced-position column on page 23 no longer starts at LMS FL Teacher; '
             'read %r' % reduced)
    out = rows_from(rel, 23, [re.sub(r'^\s*\s*', '', l) for l in reduced])
    for r in out:
        r['direction'] = 'reduction'
    added = rows_from(rel, 23, [re.sub(r'^\s*\s*', '', l) for l in lines[:8]])
    for r in added:
        r['direction'] = 'addition'
    return out + added


# ---- FY2021 ----------------------------------------------------------------------

def fy21():
    rel = DOCS[FY21]['text']
    pg = pages(rel)
    page = next((p for p, ls in pg.items()
                 if any('Potential Reductions for 2.5%' in l for l in ls)), None)
    if page is None:
        fail('the FY21 deck no longer carries a `Potential Reductions for 2.5%` slide')
    lines = block_lines(pg, page, start='FY21 School Department Targeted Budget',
                        rel=rel)
    keep = [l for l in lines if l.endswith('stays')]
    cut = [l for l in lines if not l.endswith('stays')]
    if len(cut) != 7 or len(keep) != 2:
        fail('the FY21 potential-reductions slide read %d reductions and %d retentions, '
             'not 7 and 2' % (len(cut), len(keep)))
    out = rows_from(rel, page, [re.sub(r'^\s*\s*', '', l) for l in cut])
    for r in out:
        r['direction'] = 'reduction'
    kept = rows_from(rel, page, [re.sub(r'^\s*\s*', '', l) for l in keep])
    for r in kept:
        r['direction'] = 'retained'
    return out + kept


# ---- FY2025 ----------------------------------------------------------------------

def fy25_override():
    """The two lists the School Committee published before the May 2024 ballot.

    `Cuts without Override` and `Cuts with Override`. The second is a subset of the first,
    and the difference is what the ballot question was for. The override PASSED, so the
    conditional column is what makes this register readable a year later."""
    rel = DOCS[FY25_OVR]['text']
    pg = pages(rel)
    without = block_lines(pg, 2, start='Cuts without Override',
                          stop='Cuts with Override', expect=23, rel=rel)
    with_ovr = block_lines(pg, 2, start='Cuts with Override',
                           stop='*Denotes part-time positions', expect=9, rel=rel)
    out = []
    for lines, cond in ((without, 'the override failing'), (with_ovr, 'the override passing')):
        rs = rows_from(rel, 2, lines)
        for r in rs:
            r['direction'] = 'reduction'
            r['conditional_on'] = cond
        out += rs
    return out


def fy25_esser():
    """Page 43: two columns, and the text layer interleaved them.

    The page prints twelve ESSER-funded FY24 positions and then ten cut in FY25, with each
    caption falling BELOW its own column in the extraction. This reads the ten lines
    between the second caption and the page break, and asserts the first and last of them
    so a shift cannot go unnoticed."""
    rel = DOCS[FY25_UPD]['text']
    pg = pages(rel)
    lines = block_lines(pg, 43, start='due to loss of ESSER', expect=10, rel=rel)
    if not lines[0].startswith('Instructional Coach') or \
            not lines[-1].startswith('PE Teacher'):
        fail('the FY25 ESSER cut column no longer runs Instructional Coach … PE Teacher; '
             'read %r' % lines)
    out = rows_from(rel, 43, lines)
    for r in out:
        r['direction'] = 'reduction'
        r['block'] = 'Positions CUT in the FY25 budget due to loss of ESSER'
    return out


def fy25_impacts():
    """The per-position impact slides, pages 56 to 75.

    Each slide is: a title carrying the position and its FTE, `Current staffing N`, an
    `Impacts of …` line, then the district's own bullets. The SCHOOL is the deck's footer,
    which is the LAST line of the slide's own page — `LMHS Guidance Counselors` is
    followed by `LMHS`, `Classroom Teacher … grade 6-8` by `LMS`. Reading the PREVIOUS
    page's footer instead is wrong on eight of these twenty slides and looks identical on
    the other twelve, which is why the footer is asserted to resolve to a school rather
    than assumed to."""
    rel = DOCS[FY25_UPD]['text']
    pg = pages(rel)
    out = []
    for page in range(56, 76):
        if page not in pg:
            continue
        body = [debullet(l) for l in pg[page] if l.strip()]
        body = [l for l in body if l]
        if len(body) < 3:
            continue
        footer = body[-1]
        key, printed_school = school_of(footer)
        if key == 'not stated' or len(footer) > 24:
            fail('%s page %d does not end in a school footer — it ends %r, and the school '
                 'on every row of this block is read from that line' % (rel, page, footer))
        title = body[0]
        cons = re.sub(r'\s+', ' ', ' '.join(body[1:-1])).strip()
        out.append(dict(printed=title, position=position_of(title), school=key,
                        school_printed=footer, fte=fte_of(title),
                        amount=amount_of(title), consequence=cons, page=page,
                        doc_text=rel, basis='stated', direction='reduction',
                        block='Impacts'))
    if len(out) != 20:
        fail('the FY25 impact slides read %d positions, not 20 — %r'
             % (len(out), [(r['page'], r['printed']) for r in out]))
    return out


# ---- FY2026 -----------------------------------------------------------------------

def fy26():
    """The 39 lines the School Committee approved, exactly as printed.

    No dollar figure and no consequence is printed against any of them, and the register
    leaves both empty rather than borrowing either from a neighbouring document."""
    rel = DOCS[FY26]['text']
    pg = pages(rel)
    lines = block_lines(pg, 1, start='Personnel Cuts', expect=39, rel=rel)
    out = []
    for printed in lines:
        head, _, tail = printed.partition(' - ')
        if not tail:
            fail('the FY26 approved list no longer prints `School - Position`: %r' % printed)
        key = SCHOOL_KEY.get(head.strip().lower())
        if key is None:
            fail('the FY26 approved list names a school this register does not know: %r'
                 % head)
        out.append(dict(printed=printed, position=position_of(tail), school=key,
                        school_printed=head.strip(), fte=fte_of(tail),
                        amount='', page=1, doc_text=rel, basis='stated',
                        direction='reduction', block='Personnel Cuts'))
    return out


# ---- FY2027 -----------------------------------------------------------------------

def fy27_addendum():
    rel = DOCS[FY27_ADD]['text']
    pg = pages(rel)
    out = []

    def take(page, start, stop, expect, direction, block, scenario, to_page=None):
        # The restoration list runs over a page break in the extraction, so a block is a
        # SPAN rather than a slice of one page. Both anchors are still verbatim -- and
        # EACH LINE KEEPS THE PAGE IT WAS READ FROM. Stamping the whole span with the
        # start page put seven citations on page 2 that are printed on page 3; a page
        # coordinate that is wrong is a citation nobody can follow, and
        # verify_cut_register.py now checks every row against the page it names.
        if to_page:
            pairs = ([(page, l) for l in block_lines(pg, page, start=start, rel=rel)]
                     + [(to_page, l) for l in block_lines(pg, to_page, stop=stop,
                                                          rel=rel)])
        else:
            pairs = [(page, l) for l in
                     block_lines(pg, page, start=start, stop=stop, rel=rel)]
        # `Staffing:` and `Programs:` are the document's own sub-headings INSIDE a block,
        # not rows. A line that is a heading and nothing else is dropped; anything
        # carrying a position is not.
        pairs = [(p, debullet(l)) for p, l in pairs]
        pairs = [(p, l) for p, l in pairs
                 if l and not re.fullmatch(r'[A-Za-z ]{3,20}:', l)]
        if len(pairs) != expect:
            fail('%s page %d block %r read %d rows, not %d: %r'
                 % (rel, page, block, len(pairs), expect, [l for _p, l in pairs]))
        rs = []
        for pnum, line in pairs:
            rs += rows_from(rel, pnum, [line])
        for r in rs:
            r['direction'] = direction
            r['block'] = block
            r['conditional_on'] = scenario
        return rs

    # The Balanced scenario — the no-override budget. Eight staffing reductions with a
    # dollar figure against all but one; the district's own text prints `$` and no number
    # beside the Turkey Hill music reduction, and the register leaves it empty.
    out += take(6, 'Reductions:', 'Program Reductions', 8,
                'reduction', 'Scenario D: Balanced Budget — Reductions',
                'the Balanced scenario')
    # The Core scenario buys additions by making two named losses.
    out += take(4, 'Staffing Losses:', 'Program Additions:', 2, 'reduction',
                'Scenario C: Core Budget — Staffing Losses', 'the Core scenario')
    out += take(4, 'Staffing Additions:', 'Staffing Losses:', 9, 'restoration',
                'Scenario C: Core Budget — Staffing Additions', 'the Core scenario')
    out += take(2, 'Proposed Restorations / Additions:', 'Programs:', 10, 'restoration',
                'Scenario B: Restoration Budget — Staffing', 'the Restoration scenario',
                to_page=3)
    return out


def fy27_slides():
    """The 23 March deck, one item per slide, with the district's own words beneath it.

    A slide's TITLE is the run of lines from the top until a dollar figure appears, at
    most three -- the deck sets several titles over two lines, and taking only the first
    would publish `Assistant Principal Primary/Turkey Hill` with no amount and no second
    school. A slide with no dollar figure in its first three lines is a section divider or
    the summary, and is not an item. A leading line of bare digits is the deck's own slide
    number and is dropped.

    The SECTION heading a slide sits under is what says whether an item is a reduction or
    an addition: the deck groups the three additions under `Necessary Additions` and
    everything else under an `… Impacts` heading. That is the district's own grouping and
    not our reading of the job titles."""
    rel = DOCS[FY27_SLIDES]['text']
    pg = pages(rel)
    out, section = [], ''
    for page in sorted(pg):
        body = [debullet(l) for l in pg[page] if l.strip()]
        body = [l for l in body if l]
        while body and re.fullmatch(r'\d+', body[0]):
            body = body[1:]
        if not body:
            continue
        if len(body) == 1 and '$' not in body[0]:
            section = body[0]
            continue
        title, used = '', 0
        for l in body[:3]:
            title = (title + ' ' + l).strip()
            used += 1
            if '$' in title:
                break
        if '$' not in title:
            continue
        cons = re.sub(r'\s+', ' ', ' '.join(body[used:])).strip()
        key, printed_school = school_of(title)
        if section == 'Necessary Additions':
            direction = 'addition'
        elif title.startswith('Raise Athletic Fees'):
            direction = 'revenue measure'
        else:
            direction = 'reduction'
        out.append(dict(printed=title, position=position_of(title), school=key,
                        school_printed=printed_school, fte=fte_of(title),
                        amount=amount_of(title), consequence=cons, page=page,
                        doc_text=rel, basis='stated', direction=direction,
                        block=section, conditional_on='the Balanced scenario'))
    if len(out) != 19:
        fail('the 23 March balanced-budget deck read %d itemised slides, not 19 — %r'
             % (len(out), [r['printed'] for r in out]))
    if not any(r['direction'] == 'addition' for r in out):
        fail('the 23 March deck no longer groups any slide under `Necessary Additions`, '
             'so every item on it would be published as a reduction')
    return out


BLOCKS = [
    (FY20_MAR, 'Recommended Reductions', 'reduction', fy20_march),
    (FY20_MEMO, 'The following cuts are recommended', 'reduction', fy20_memo),
    (FY20_FINAL, 'Superintendent’s Recommended FY20 Budget (3.0%)', 'reduction',
     fy20_final),
    (FY21, 'Potential Reductions for 2.5%', 'reduction', fy21),
    (FY25_OVR, 'Cuts without / with Override', 'reduction', fy25_override),
    (FY25_UPD, 'Positions CUT in the FY25 budget due to loss of ESSER', 'reduction',
     fy25_esser),
    (FY25_UPD, 'Impacts', 'reduction', fy25_impacts),
    (FY26, 'Personnel Cuts', 'reduction', fy26),
    (FY27_ADD, 'Scenarios B, C and D', 'reduction', fy27_addendum),
    (FY27_SLIDES, 'Balanced Budget', 'reduction', fy27_slides),
]


def build():
    sha = sha_index()
    rows = []
    for key, block, default_direction, fn in BLOCKS:
        d = DOCS[key]
        got = fn()
        if not got:
            fail('the block %r in %s produced no rows' % (block, d['text']))
        for r in got:
            r.setdefault('block', block)
            r.setdefault('direction', default_direction)
            r.setdefault('conditional_on', '')
            r.setdefault('consequence', '')
            r['fy'] = d['fy']
            r['doc_date'] = d['doc_date']
            r['doc_title'] = d['doc_title']
            r['stage'] = d['stage']
            r['doc_pdf'] = d['pdf']
            r['sha256'] = sha.get(d['pdf'], '')
            if not r['sha256']:
                fail('%s is not in the archive manifest, so this register would publish '
                     'a citation with no hash behind it (rule 12)' % d['pdf'])
            rows.append({k: r.get(k, '') for k in FIELDS})

    # EVERY `printed` AND `consequence` STRING MUST STILL BE IN THE DOCUMENT IT IS
    # ATTRIBUTED TO. The parsers already read it out of there; this is the assertion that
    # survives somebody editing a parser to hand-fill a row, and it is what makes rule 13
    # mechanical here rather than a habit.
    #
    # Both sides are normalised the same way and only the same way: the bullet glyphs and
    # the line breaks are the EXTRACTOR'S rendering of the page, not the district's words,
    # and a deck's bullet arrives in the text layer as a Wingdings private-use character.
    # Nothing else is touched -- no case folding, no punctuation, no spelling -- so a
    # changed word still fails.
    def norm(t):
        t = re.sub(r'[\u2022\u25cb\u25cf\u25aa\u00b7\uf000-\uf0ff]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        # A lone punctuation mark on its own line is a decorative glyph the deck sets
        # beside a bullet -- a `$` icon, an arrow -- and the extractor gives it a line of
        # its own. Dropped on BOTH sides and only when it stands alone, so `$106,537`,
        # which is a token of five characters, is untouched and a changed figure still
        # fails this check.
        return re.sub(r'\s+', ' ',
                      re.sub(r'(?<!\S)[^\w\s](?!\S)', ' ', t)).strip()

    cache = {}
    for r in rows:
        body = cache.setdefault(
            r['doc_text'],
            norm(open(os.path.join(TEXT, r['doc_text']), encoding='utf-8',
                      errors='replace').read()))
        for field in ('printed', 'consequence'):
            want = norm(r[field])
            if want and want not in body:
                fail('%s: %s %r is not in %s. Quote the source, never your rendering '
                     'of it.' % (r['doc_title'], field, want[:90], r['doc_text']))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    buf = []
    import io
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    text = s.getvalue()
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != text:
            print('STALE — %s is not what the documents now produce. '
                  'Run scripts/extract_stated_cuts.py.' % rel)
            return 1
        print('ok — %s reproduces from the documents' % rel)
        return 0
    open(OUT, 'w', encoding='utf-8').write(text)
    fys = sorted({r['fy'] for r in rows})
    print('wrote %s — %d stated changes across %d documents, FY%s to FY%s'
          % (rel, len(rows), len({r['doc_text'] for r in rows}), fys[0], fys[-1]))
    for fy in fys:
        f = [r for r in rows if r['fy'] == fy]
        print('  FY%s  %3d rows  %d reductions  %d restorations/additions  %d documents'
              % (fy, len(f),
                 sum(1 for r in f if r['direction'] == 'reduction'),
                 sum(1 for r in f if r['direction'] in ('restoration', 'addition')),
                 len({r['doc_text'] for r in f})))
    _ = buf
    return 0


if __name__ == '__main__':
    sys.exit(main())
