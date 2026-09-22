#!/usr/bin/env python3
"""Who held every town post, board by board, out of the annual report's personnel listing.

TJ, 21 September 2026, after I reported that the annual reports carry no organisational
charts: *"org charts DO exist in annual reports... its not called an org chart. its
personell listing for each department and board"*. He was right. I had grepped for
`organizational chart`, found nothing in five years, and reported my matcher's failure as
a fact about the town -- rule 13c, for the sixth time -- when the thing itself runs to
nine or ten pages in every book under ELECTED OFFICIALS and APPOINTED OFFICIALS, and was
already catalogued in our own extraction plan with per-year notes I had not read.

**WHY THIS IS WORTH READING.** A budget line that falls is not a cut, and a cut is a
service reduction. The nearest published thing to a service level is who the town employs
and appoints, and the wage list stopped naming departments after FY2016. This listing did
not stop: it names every board, every appointed post and every holder, with the year their
term runs out, for every year we hold.

**THE HEADING STATES THE BOARD'S SIZE, so the page checks itself.** `COUNCIL ON AGING-(11
members) 3 year term` is followed by eleven names. That is an identity the document states
about itself, exactly like a printed grand total, and it is the difference between reading
this listing and guessing at it: eighteen to twenty headings a year carry one. A board
whose names do not come to its stated size is reported rather than published.

**AND THE FORMAT IS NOT THE SAME EVERY YEAR** -- TJ again, before a line of this was
written: *"just make sure you dont assume this format is the same for every year"*.
FY2022 and FY2023 open the listing on page 7; FY2025 on page 10. FY2023 began adding
`-appointed 9/2023` notes after a name. So the page range is discovered from the headings
rather than hardcoded, and a year that produces no `(N members)` heading at all is refused
rather than trusted, because that is the signature of a layout this does not understand.

    python3 scripts/extract_personnel.py            # every year it can find
    python3 scripts/extract_personnel.py --check    # ...and fail if a stated size disagrees
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
OUT = os.path.join(ROOT, 'sources', 'data', 'town-personnel.csv')

SECTION = re.compile(r'^(ELECTED|APPOINTED)\s+OFFICIALS\b', re.I)
# THE PARENTHESIS DOES NOT ALWAYS CLOSE AFTER `members`. `STORM WATER TASK FORCE (5
# members as of Nov. 2021)` states its size as plainly as any other heading, and a pattern
# demanding `members)` refused it -- so the task force was read as a PERSON standing under
# `RECREATION DIRECTOR`, which is how a one-person post came to list six. Take the count
# where it is stated and ignore whatever else the town put inside the brackets.
SIZE = re.compile(r'\(\s*(?:no less than \d+ and no more than\s*)?(\d+)\s*members?\b'
                  r'[^)]*\)', re.I)

# A RANGE IS NOT A SIZE. Several bodies are constituted with a floor and a ceiling --
# `CULTURAL COUNCIL (no less than 5 and no more than 22 members)`, `HISTORICAL COMMISSION-
# 3 year term (not less than 3 nor more than 7 members)` -- and testing the names against
# the ceiling reported a perfectly legal ten-member council as a failure. Where the
# heading states a range the check is that the count falls INSIDE it.
RANGE = re.compile(r'\(?\s*(?:no|not)\s+less\s+than\s+(\d+)\s+(?:and|nor)\s+'
                   r'(?:no|not)?\s*more\s+than\s+(\d+)', re.I)
TERM = re.compile(r'[-–]\s*(20\d\d)\s*$')
APPOINTED_NOTE = re.compile(r'[-–]\s*(appointed|resigned|retired|deceased|term|vacan)', re.I)
PAGENO = re.compile(r'^\d{1,3}$')

# AN EMPTY SEAT IS NOT A PERSON NAMED `Vacancy`, and counting it as one was inflating
# every figure on the page. The town prints its empty seats, in eight spellings across
# four years -- `Vacant`, `Vacancy`, `1Vacancy`, `1 Vacancy`, `Vacancies`,
# `2 Associate Member Vacancies`, `Vacant-Select Board Representative`, `Vacant-
# Conservation Commission` -- and some carry a count in front of the word.
#
# It is worth getting right rather than filtering out, because it is the most actionable
# thing in the whole listing: an empty seat is a seat a resident can ask to fill, and the
# town publishes exactly where they are.
# NOT THE TOWN. The listing opens with a directory of the offices a Lunenburg resident is
# represented BY -- the Governor, the Attorney General, the state senate and house seats,
# the congressional delegation -- printed with mailing addresses at the State House and in
# Washington. They are offices of the Commonwealth and of the United States, and reading
# them as town posts put 199 rows and seven "departments" into a page called who runs the
# town, inflating every count on it.
#
# The cut is per POST rather than per page, because the directory spills onto a second page
# in three of the four years and a page rule would have to guess where it stops.
STATE_FEDERAL = re.compile(
    r"^(?:GOVERNOR|LIEUTENANT\s+GOVERNOR|GOVERNOR'?S\s+COUNCIL|ATTORNEY\s+GENERAL"
    r"|SECRETARY\s+OF\s+(?:THE\s+)?(?:STATE|COMMONWEALTH)|STATE\s+(?:TREASURER|AUDITOR)"
    r"|AUDITOR\b|TREASURER\s+AND\s+RECEIVER|SENATE\b|SENATOR\b|STATE\s+LEGISLATORS"
    r"|HOUSE\s+OF\s+REPRESENTATIVES|REPRESENTATIVE\s+IN\s+CONGRESS"
    r"|U\.?\s?S\.?\s+(?:SENATOR|REPRESENTATIVE)|ELECTED\s+OFFICIAL\b)", re.I)

# `MASSACHUSETTS CONGRESSIONAL DELEGATION` does not start with any of the above, and one
# year prints it `COAGRESSIONAL` -- so this one is matched anywhere in the heading and
# spelled loosely enough to survive a scanner reading N as A. Anchoring it left 72 rows of
# the state directory in a page about the town.
CONGRESS = re.compile(r'C[O0][NAM]GRESS', re.I)

VACANCY = re.compile(r'^\s*(\d+)?\s*(?:associate member\s+)?vacan(?:t|cy|cies)\b', re.I)

# `terms`, PLURAL, and it cost a dozen headings. `\bterm\b` does not match `(3 year
# terms)`, so ECONOMIC DEVELOPMENT COMMITTEE failed the constitution test, fell through to
# the capitals test -- where `year terms` in lower case drags the ratio to 0.75 -- and was
# read as a PERSON standing under whatever heading came before it. That is how `DPW
# DIRECTOR`, a post held by one person, came to list nine.
TERMLEN = re.compile(r'\b\d+\s*years?\s*terms?\b', re.I)

# `Ex Officio Members`, `Associate Members` -- a roster WITHIN a body, printed in title
# case with no membership stated. Read as people they inflate the body above them.
SUBROSTER = re.compile(r'^(?:ex[- ]officio|associate|alternate|student|honorary)\s+'
                       r'members?\b', re.I)

# What follows a name and is not part of it: an appointment, a resignation, a role.
APPOINTED_NOTE = re.compile(r'[-–]\s*(appointed|resigned|retired|deceased|term|vacan)',
                            re.I)


FIELDS = ['fy', 'page', 'order', 'post', 'kind', 'section', 'stated_members',
          'person', 'vacancies', 'term_expires', 'note', 'size_check']


WORDS = os.path.join(ROOT, 'sources', 'town-budget', 'ocr', 'words')

# THE ARCHIVED LINE TSVs CONTAIN A 123,577-CHARACTER FIELD, and csv refuses it by default.
# ocr_pdf.swift's own comment records why: a Vision observation can CONTAIN a newline, and
# written straight into a TSV it terminates the row early so every following row is
# absorbed into the last field until the reader recovers. The writer sanitises now; the
# files on disk were produced before it did. Raising the limit reads them as they are
# rather than rewriting history, and a field that large is visible as nonsense to anything
# that looks at it.
csv.field_size_limit(10_000_000)

# The listing is always in the front of the book; the budget tables that would
# otherwise look like it by capitals alone are never this early.
FRONT_MATTER = 30

# A CONTENTS PAGE LOOKS EXACTLY LIKE THE LISTING to any test that counts capitals and
# title case: `ELECTED OFFICIALS`, `PROTECTION OF PERSONS & PROPERTY` over `Town Manager`,
# `Board of Health`, `Fire Department`. It swept 115 phantom people into FY2022 alone. It
# also says what it is at the top of itself, which is cheaper and surer than any shape
# test on the lines beneath.
CONTENTS = re.compile(r'table\s+of\s+cont', re.I)


def word_rows(fy):
    """Every recognised WORD on the listing pages of one year, with its own box.

    `ocr_pdf.swift --boxes` writes one row per Vision OBSERVATION and an observation is a
    LINE, so on a two-column page its box spans both columns: FY2022 page 9 came back as
    27 observations for 27 printed lines with every x-centre between 0.495 and 0.500.
    There was nothing to cluster on, and rule 13b's method -- measure the page, place by
    position -- had no position to measure. `ocr_words.swift` asks Vision for a box per
    word instead, which it will give for any character range, and the same nine pages come
    back as 1,205 boxes.
    """
    path = os.path.join(WORDS, 'fy%s.words.tsv' % fy)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            x, y, w, h = (float(r['x']), float(r['y']), float(r['w']), float(r['h']))
            out.append(dict(page=int(r['page']), x0=x, x1=x + w, cy=y + h / 2,
                            text=r['text']))
    return out


def rows_of(words):
    """Words grouped into printed ROWS, with the band measured off the page.

    Rule 13b: the band is half the page's own median row pitch, never a constant. A page
    set in a larger face then needs no new number.
    """
    words = sorted(words, key=lambda w: -w['cy'])
    ys = sorted({round(w['cy'], 4) for w in words}, reverse=True)
    gaps = sorted(a - b for a, b in zip(ys, ys[1:]) if a - b > 0.002)
    band = (gaps[len(gaps) // 2] / 2) if gaps else 0.008
    rows = []
    for w in words:
        if rows and abs(rows[-1][0] - w['cy']) <= band:
            rows[-1][1].append(w)
        else:
            rows.append([w['cy'], [w]])
    return [(cy, sorted(ws, key=lambda w: w['x0'])) for cy, ws in rows]


def cells_of(rows):
    """Each row split into CELLS at the column breaks, measured against the page itself.

    A column break is whitespace, and whitespace is measurable now that boxes are words:
    the median gap between adjacent words on these pages is 0.0028 of the page width and a
    break is over 0.05 -- eighteen times. So the threshold is derived from the page (ten
    times its own median) rather than picked, and a page with no such gap yields one cell
    per row and is left exactly as it was.
    """
    gaps = [b['x0'] - a['x1'] for _cy, ws in rows for a, b in zip(ws, ws[1:])]
    gaps = [g for g in gaps if g > 0]
    med = sorted(gaps)[len(gaps) // 2] if gaps else 0.003
    cut = max(med * 10, 0.02)
    out = []
    for cy, ws in rows:
        cells, cur = [], [ws[0]]
        for a, b in zip(ws, ws[1:]):
            if b['x0'] - a['x1'] > cut:
                cells.append(cur)
                cur = []
            cur.append(b)
        cells.append(cur)
        out.append((cy, cells))
    return out


def read_order(page, rows):
    """(column-id, text) in the order a person reads the page.

    A LISTING PAGE IS NOT UNIFORMLY TWO-COLUMN. Most of it runs down the middle in one
    column and then a handful of rows put two posts side by side -- `ANIMAL CONTROL
    OFFICER` beside `ANIMAL INSPECTOR`, each with its own holder beneath. Treating the
    whole page as two columns splits the single-column rows down the middle; treating it
    as one runs the pairs together into one post with the wrong name.

    So a RUN of consecutive rows that all split into the same number of cells is a block,
    and a block of width two is read column-wise: every left cell, then every right cell.
    A block of width one is read straight down. The column id is returned with each entry
    because a heading may not own names in another column, and the boundary is where a
    post is closed.
    """
    out, i = [], 0
    while i < len(rows):
        width = len(rows[i][1])
        j = i
        while j < len(rows) and len(rows[j][1]) == width:
            j += 1
        for c in range(width):
            for k in range(i, j):
                cell = rows[k][1][c]
                t = ' '.join(w['text'] for w in cell).strip()
                if t:
                    out.append(((page, i, c), t))
        i = j
    return out


def line_tsv(fy):
    """The line-level TSV for one year, found on disk rather than tabulated.

    A hardcoded map of four years is a latent break with a date on it -- the repo's own
    most common defect, a LOCATION written down where location is not identity. The
    documents are numbered by the town and renumbering has already moved them once.
    """
    hits = glob.glob(os.path.join(ROOT, 'sources', 'town-budget', 'ocr',
                                  '*fy-%s-annual-town-report.tsv' % fy))
    return hits[0] if hits else ''


def line_rows(fy):
    """The LINE observations, which are the authority for TEXT.

    TWO INSTRUMENTS, EACH DOING WHAT IT IS GOOD AT. The word pass exists because a line
    box spans both columns and cannot place anything; but the word pass does not read the
    page as WELL. On FY2022 page 8 it returns no Housing Authority members at all, while
    the line pass has Catherine J. Clark, Linda M. McDonald and Dale Proulx sitting there
    -- and it is not a dropped box, because the fallback that would have caught that fires
    zero times. Vision simply recognises differently under a different render.

    A board that states five members and yields none is the worst possible failure here,
    because it is indistinguishable from a board nobody joined. So the line pass supplies
    the words and the word pass supplies only the x positions used to cut a line into
    columns. Text can never be lost by a geometry that is missing; at worst a line stays
    whole, which is what it used to be.
    """
    path = line_tsv(fy)
    if not path or not os.path.exists(path):
        return []
    out = []
    with open(path, encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            try:
                y, h = float(r['y']), float(r['h'])
            except (ValueError, KeyError):
                continue
            x, w = float(r['x']), float(r['w'])
            out.append(dict(page=int(r['page']), cy=y + h / 2, x0=x, x1=x + w,
                            text=r['text']))
    return out


def cut_line(text, words):
    """One printed line, cut into cells wherever its own words leave a column gap.

    The words are the ruler and the line is the reading. Where no words are found for a
    line -- the two passes disagree about what is on the page -- the line is returned
    whole rather than guessed at.
    """
    if len(words) < 2:
        return [text]
    gaps = [(b['x0'] - a['x1'], a, b) for a, b in zip(words, words[1:])]
    pos = [g for g in gaps if g[0] > 0]
    if not pos:
        return [text]
    med = sorted(g[0] for g in pos)[len(pos) // 2]
    cut = max(med * 10, 0.02)
    breaks = [i for i, (g, _a, _b) in enumerate(gaps) if g > cut]
    if not breaks:
        return [text]
    # Cut the TEXT at the same word ordinals the geometry broke at.
    toks = text.split()
    if len(toks) != len(words):
        return [text]
    cells, prev = [], 0
    for b in breaks:
        cells.append(' '.join(toks[prev:b + 1]))
        prev = b + 1
    cells.append(' '.join(toks[prev:]))
    return [c for c in cells if c.strip()]


def lines_of(path_or_fy):
    """(column-id, section, text) in reading order: line text, word geometry."""
    words = word_rows(path_or_fy)
    wpage = collections.defaultdict(list)
    for w in words:
        wpage[w['page']].append(w)
    lpage = collections.defaultdict(list)
    for r in line_rows(path_or_fy):
        lpage[r['page']].append(r)
    for page in sorted(lpage):
        lines = sorted(lpage[page], key=lambda r: -r['cy'])
        wrows = rows_of(wpage.get(page, []))
        head = lines[0]['text'].strip() if lines else ''
        m = SECTION.match(head)
        section = m.group(1).lower() if m else ''
        # BAND THE LINES BY y FIRST, because two columns are often two separate Vision
        # observations rather than one wide one. FY2022 page 12 prints `DAM KEEPER` beside
        # `ASSISTANT DAM KEEPER` with `Ronald Wilson` and `Richard Patry` beneath them, and
        # Vision returns four observations. There is no gap INSIDE any of them to cut, so
        # cutting lines was never going to find it -- read one after another they become
        # two posts with no holders and then two people under the wrong one.
        #
        # Banded by y and sorted by x, they are what they are: one row of two cells, then
        # another. The band is half the page's own median line pitch, rule 13b.
        ys = sorted({round(l['cy'], 4) for l in lines}, reverse=True)
        pitch = sorted(a - b for a, b in zip(ys, ys[1:]) if a - b > 0.002)
        band = (pitch[len(pitch) // 2] / 2) if pitch else 0.008
        banded = []
        for ln in lines:
            if banded and abs(banded[-1][0] - ln['cy']) <= band:
                banded[-1][1].append(ln)
            else:
                banded.append((ln['cy'], [ln]))
        rows = []
        for cy, group in banded:
            group.sort(key=lambda l: l['x0'])
            cells = []
            for ln in group:
                near = min(wrows, key=lambda r: abs(r[0] - ln['cy'])) if wrows else None
                ws = near[1] if (near and abs(near[0] - ln['cy']) < 0.006) else []
                # only use the word cut when this observation spans the words we found
                inside = [w for w in ws if w['x0'] >= ln['x0'] - 0.01
                          and w['x1'] <= ln['x1'] + 0.01]
                cells += cut_line(ln['text'], inside)
            rows.append((cy, cells))
        for col, t in read_order_text(page, rows):
            yield col, section, t


def read_order_text(page, rows):
    """As read_order, over cells that are already text."""
    out, i = [], 0
    while i < len(rows):
        width = len(rows[i][1])
        j = i
        while j < len(rows) and len(rows[j][1]) == width:
            j += 1
        for c in range(width):
            for k in range(i, j):
                t = rows[k][1][c].strip()
                if t:
                    out.append(((page, i, c), t))
        i = j
    return out


def split_entries(raw):
    """One printed line, into the entries actually on it.

    Some pages set two or three names across the width and the flattened text runs them
    together: `Maryrae Holman-Agricultural Commission Cathy Clark-Member at Large` is two
    people, and `Louis Franco-Select Board Adam Burney-Land Use Director Matthew
    Brenner-Planning` is three. The gutter detector does not catch these because the
    columns on such a page are not separated by a blank channel on enough lines to
    measure.

    What IS still in the text is the run of spaces between them, so split on three or
    more. Two spaces is not enough -- proportional text flattened to a monospace grid puts
    two spaces inside ordinary names -- and a line with no such run comes back whole.
    """
    parts = [p for p in re.split(r'\s{3,}', raw.strip()) if p.strip()]
    return parts or ['']


def is_heading(t):
    """A POST says how it is constituted. A PERSON does not.

    The first version of this tested CASE -- capitals are a post, title case is a person --
    and TJ had already warned that the format is not the same every year. It is not: the
    APPOINTED pages print `INSPECTOR OF WIRING`, and the ELECTED pages print `Board of
    Assessors - (3 members) 3 year term`, so a case test reads an entire page of the
    listing as one long list of people under no post at all.

    What every heading carries, in both styles and all four years, is its own constitution:
    `(3 members)`, `3 year term`, or both. That is the same kind of signal as a printed
    total -- the document saying what it is about to show -- and it does not care how the
    year chose to set the type. Capitals stay as a second test, because a single-holder
    post like `DPW DIRECTOR` has no membership to state.

    It also makes `Associate Members—(2) 2 year term` a post in its own right, which is
    what it is: the Agricultural Commission states five members and lists four plus two
    associates, and reading the associates into the commission was what made it nine.
    """
    if SIZE.search(t) or TERMLEN.search(t) or SUBROSTER.match(t):
        return True
    head = post_name(t)
    letters = [c for c in head if c.isalpha()]
    if len(letters) < 3:
        return False
    upper = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper > 0.85 and bool(re.search(r'[A-Z]{3}', head))


def post_name(t):
    """The post, with the constitution it stated taken back off the end.

    Stripping `(5 members)` and `3 year term` leaves debris a resident then reads in the
    vacancies table, which is the first thing on the page: `PLANNING BOARD - 2` out of
    `- 2 - 5 year terms`, and `ARCHITECTURAL PRESERVATION DISTRICT COMMISSION (APDC` with
    the bracket never closed because the membership pattern took the closing paren with it.

    The first repair was worse than the fault -- balancing brackets blindly produced a post
    called `()` -- so it strips repeatedly until nothing more comes off, and only closes a
    bracket that has something inside it.
    """
    t = re.sub(r'\s+', ' ', TERMLEN.sub('', SIZE.sub('', t))).strip()
    for _ in range(4):
        before = t
        t = re.sub(r'[-–,;:\s]+$', '', t)          # trailing punctuation
        t = re.sub(r'\(\s*\)$', '', t)             # an empty bracket
        t = re.sub(r'\(\s*$', '', t)               # a bracket with nothing after it
        t = re.sub(r'[-–]\s*\d+$', '', t)          # an orphan `- 2`
        t = re.sub(r'\s*/\s*$', '', t)
        if t == before:
            break
    if t.count('(') > t.count(')') and re.search(r'\([^)]{2,}$', t):
        t += ')'
    return t.strip(' -–,')


def listing_pages(path):
    """The pages of the listing, found from what is ON them, not from a running header.

    The first version looked for `ELECTED OFFICIALS` or `APPOINTED OFFICIALS` as the first
    line of a page, because that is how FY2016 onward print it. Five years do not:
    FY2019 and FY2021 open the section on a page headed `MASSACHUSETTS CONGRESSIONAL
    DELEGATION`, and FY2011 to FY2013 print the listing with NO running header anywhere.
    Reading the header's absence as the section's absence lost five years -- rule 13c,
    which is the rule I have broken most often in this repo.

    So a listing page is one that LOOKS like the listing: several posts, each stating a
    membership or a term or printed in capitals, with names under them. Restricted to the
    front matter, because a budget page carries plenty of capitals and no people.
    """
    pages = collections.defaultdict(lambda: [0, 0, 0])
    header, first, contents = set(), {}, set()
    for col, _sec, t in lines_of(path):
        page = col[0]
        if page > FRONT_MATTER:
            continue
        if page not in first and t.strip():
            first[page] = t.strip()
            if SECTION.match(t.strip()):
                header.add(page)
            if CONTENTS.search(t):
                contents.add(page)
        # THE SIGNATURE IS A POST STATING HOW IT IS CONSTITUTED, not capitals. Counting
        # any capitalised line pulled in the warrant, the dedication and the meeting
        # schedule -- all front matter, all shouty -- and doubled every year's count.
        # `Board of Assessors - (3 members) 3 year term` appears on no other kind of page.
        if SIZE.search(t) or TERMLEN.search(t):
            pages[page][0] += 1
            pages[page][2] += 1
        elif is_heading(t):
            pages[page][2] += 1
        elif len(re.findall(r'[A-Za-z]', t)) >= 5:
            pages[page][1] += 1
    # BOTH SIGNALS, UNIONED. The running header is the better test where a year prints one
    # -- it catches a page of single-holder posts that states no membership anywhere, and
    # requiring two constituted posts lost 54 people in FY2016 alone. The content test is
    # the only test where a year prints no header at all. Neither is sufficient and each
    # is sound, so a page qualifying under either is a listing page.
    content = {pg for pg, (constituted, people, _posts) in pages.items()
               if constituted >= 2 and people >= 3}
    seed = (header | content) - contents
    if not seed:
        return seed
    # THEN GROW THE RUN. The strict test FINDS the section; it does not measure it. A page
    # of single-holder officers -- `INSPECTOR OF WIRING`, `LOCAL CENSUS LIAISON`, a name
    # under each -- states no membership anywhere and fails the test that found the
    # section, so FY2019 stopped at page 16 and left page 17 of its own listing unread.
    # The listing is contiguous, so extend outward from the seed while the next page still
    # looks like the listing at all, and stop at the first page that does not.
    # AND THE WALK STOPS AT A PAGE WITH NO POST ON IT. Growing on `enough lines that look
    # like names` walked FY2025 back from its listing at page 10 to page 3 -- the profile
    # and dedication pages, where `Lunenburg Profile` and a list of department names read
    # as posts and people. A page of the listing always carries at least one thing
    # constituted or capitalised as a post; front matter carries none.
    # THE WALK GROWS ON POSTS, NOT ON NAMES. FY2019 page 17 is the listing -- `INSPECTOR
    # OF WIRING`, `LOCAL CENSUS LIAISON`, a name under each -- and states no membership
    # anywhere, so growing on `constituted` alone stopped at page 16 and lost 71 people.
    # Growing on anything name-shaped instead walked FY2025 back into its profile and
    # dedication pages. A page of the listing is a page of POSTS: several lines that are
    # headings, whether or not any of them states a size.
    loose = {pg for pg, (_c, people, posts) in pages.items()
             if posts >= 4 and people >= 3}
    out = set(seed)
    for step in (1, -1):
        pg = (max(seed) if step == 1 else min(seed)) + step
        while 0 < pg <= FRONT_MATTER and pg in loose and pg not in contents:
            out.add(pg)
            pg += step
    return out


def _says(stated):
    if stated is None:
        return ''
    return f'{stated[0]}-{stated[1]}' if isinstance(stated, tuple) else str(stated)


def close_post(rows, post, stated, seen, problems, fy):
    """Stamp every row of the post just finished with what its own heading proves.

    THREE STATES, NEVER TWO, for the same reason the annual-report extracts have three:
    `checked` where the heading states a size and that many people are named; `check
    failed` where it states one and a different number are named; `no check` where the
    heading states no size at all, which is most single-holder posts and is not a doubt
    about the reading. Nothing may be counted without splitting on this column -- a board
    listing six people against five seats is usually a mid-year replacement printed beside
    the person it replaced, and summing it as six inflates the town.
    """
    if not post:
        return
    if stated is None:
        state = 'no check'
    elif isinstance(stated, tuple):
        state = 'checked' if stated[0] <= seen <= stated[1] else 'check failed'
    else:
        state = 'checked' if seen == stated else 'check failed'
    for r in rows:
        if r['post'] == post and r['fy'] == fy and not r['size_check']:
            r['size_check'] = state
    if state == 'check failed':
        says = (f'{stated[0]}-{stated[1]}' if isinstance(stated, tuple) else stated)
        problems.append(f'FY{fy} {post}: states {says} members, {seen} named')


def read_year(fy, path):
    rows, problems = [], []
    keep = listing_pages(path)
    if not keep:
        return [], []
    post, stated, seen, kind = None, None, 0, ''
    order = 0
    where = None
    for col, section, raw in lines_of(path):
        page = col[0]
        if page not in keep:
            continue
        # A HEADING CANNOT OWN NAMES IN ANOTHER COLUMN. This is how a one-person
        # directorship collected eight people: `DPW DIRECTOR` sits near the foot of the
        # left column, the right column opens with a committee's worth of names, and the
        # columns are read one after the other -- so every name at the top of column two
        # landed under the last heading of column one. Closing the post at each boundary
        # is the whole fix, and it is the same rule the page itself obeys: a column starts
        # a new run.
        # A COLUMN BOUNDARY IS NOT ALWAYS A NEW POST, and treating it as one cost 43
        # people in FY2022 alone. Two cells in a row mean one of two things and the page
        # does not label which: two posts printed side by side -- `DAM KEEPER` beside
        # `ASSISTANT DAM KEEPER`, each with its holder beneath -- or ONE post whose holders
        # are laid out across the width, which is how `DPW DIRECTOR` prints `Rob Oliva
        # (Resigned March 2022)` next to `William Bernard (Appointed May 10, 2022)`.
        #
        # What tells them apart is what the new column STARTS with. A heading opens a post
        # and closes the one before it, which the loop below already does. A person
        # continues the post that is open. So the boundary itself does nothing, and only a
        # page break -- where nothing can continue -- closes a post outright.
        if where is not None and where[0] != col[0]:
            close_post(rows, post, stated, seen, problems, fy)
            post, stated, seen, kind = None, None, 0, ''
        where = col
        for t in split_entries(raw):
            t = t.strip()
            if PAGENO.match(t) or SECTION.match(t):
                    continue
            if is_heading(t):
                close_post(rows, post, stated, seen, problems, fy)
                if STATE_FEDERAL.match(post_name(t)) or CONGRESS.search(t):
                    post, stated, seen, kind = None, None, 0, ''
                    continue
                m = SIZE.search(t)
                rng = RANGE.search(t)
                # A POST THAT STATES A MEMBERSHIP IS A BOARD SEAT; one that does not is an
                # OFFICER. That is the document's own distinction -- `Board of Assessors - (3
                # members) 3 year term` against `DPW DIRECTOR` -- and it is the only one here
                # that is read rather than assumed. It is NOT paid against unpaid: this listing
                # never says what anybody is paid, and the wage list stopped naming departments
                # after FY2016, so any split on salary would be us inventing one. Rule 7.
                kind = 'board seat' if (m or TERMLEN.search(t)) else 'officer'
                # elected + board seat -> a seat the voters fill.
                # appointed + board seat -> a seat the Select Board fills: a volunteer member.
                # appointed + officer   -> a post somebody is HIRED into: the Town Manager,
                #                          the DPW Director, the Superintendent's office.
                # All three are the town's own distinction, read off the section header and
                # off whether the post states a membership.
                post, seen = post_name(t), 0
                stated = ((int(rng.group(1)), int(rng.group(2))) if rng
                          else int(m.group(1)) if m else None)
                continue
            if not post:
                continue
            kind = kind if post else ''
            # A person. The term year and any note travel with them, never into the name.
            vac = VACANCY.match(t)
            if vac:
                n = int(vac.group(1)) if vac.group(1) else 1
                seen += n
                order += 1
                rows.append({'fy': fy, 'page': page, 'order': order, 'post': post,
                             'section': section, 'kind': kind,
                             'stated_members': stated if stated is not None else '',
                             'person': '', 'vacancies': n,
                             'term_expires': '', 'note': t.strip(), 'size_check': ''})
                continue
            term = TERM.search(t)
            note = ''
            name = t
            if term:
                name = t[:term.start()].strip(' -–')
            elif APPOINTED_NOTE.search(t):
                i = APPOINTED_NOTE.search(t).start()
                name, note = t[:i].strip(' -–'), t[i:].strip(' -–')
            if len(re.findall(r'[A-Za-z]', name)) < 3:
                continue
            seen += 1
            order += 1
            rows.append({'fy': fy, 'page': page, 'order': order, 'post': post,
                         'section': section, 'kind': kind, 'stated_members': stated if stated is not None else '',
                         'person': re.sub(r'\s+', ' ', name), 'vacancies': 0,
                         'term_expires': term.group(1) if term else '', 'note': note,
                         'size_check': ''})
    close_post(rows, post, stated, seen, problems, fy)
    return rows, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--since', type=int, default=2011)
    args = ap.parse_args()

    rows, problems, refused = [], [], []
    # DRIVEN BY THE LINE TSVs, NOT THE WORD ONES. The word pass supplies geometry and
    # every year does not have it yet; a year without it reads with its lines whole, which
    # is what every year did before the word pass existed. Iterating the word files meant
    # five years with a perfectly readable listing were never opened at all.
    for path in sorted(glob.glob(os.path.join(ROOT, 'sources', 'town-budget', 'ocr',
                                              '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-annual', path)
        if not m or int(m.group(1)) < args.since:
            continue
        fy = int(m.group(1))
        got, probs = read_year(fy, str(fy))
        # A YEAR WITH NO STATED SIZE ANYWHERE IS A LAYOUT WE DO NOT UNDERSTAND, not a year
        # with no boards. Every year read so far prints eighteen to twenty of them.
        if not any(r['stated_members'] for r in got):
            refused.append(f'FY{fy}: no `(N members)` heading found — layout not recognised')
            continue
        rows += got
        problems += probs

    by_fy = collections.Counter(r['fy'] for r in rows if not r['vacancies'])
    vac = sum(r['vacancies'] for r in rows)
    posts = collections.Counter(fy for fy, _ in {(r['fy'], r['post']) for r in rows})
    checked = sum(1 for r in rows if r['stated_members'])
    print(f'{sum(by_fy.values())} people and {vac} printed vacancies '
          f'across {len(by_fy)} years')
    for fy in sorted(by_fy):
        print(f'  FY{fy}: {by_fy[fy]:4} people in {posts[fy]:3} posts')
    print(f'  {checked} of {len(rows)} sit under a post that states its own size')
    for r in refused:
        print(f'  REFUSED {r}')
    for p in problems[:14]:
        print(f'  MISMATCH {p}')
    if len(problems) > 14:
        print(f'  ...and {len(problems) - 14} more')

    state = collections.Counter(r['size_check'] for r in rows)
    kinds = collections.Counter(f"{r['section']} {r['kind']}" for r in rows)
    print('  by check: ' + ', '.join(f'{v} {k}' for k, v in state.most_common()))
    print('  by kind : ' + ', '.join(f'{v} {k}' for k, v in kinds.most_common()))
    # A CHECK NEVER WRITES. The first version printed its findings, exited non-zero on a
    # refusal, and then wrote the file anyway -- so `--check` repaired the thing it was
    # asked to inspect and could never report a stale file twice.
    if args.check:
        # READ IT WITH newline='' OR THE COMPARISON IS AGAINST A DIFFERENT FILE. csv
        # writes CRLF; a plain read translates it to LF, so every byte after the first
        # line differs and a current file reports stale forever. This exact bug is written
        # down in CLAUDE.md, from check_generated.py's first run, and I wrote it again.
        cur = (open(OUT, encoding='utf-8', newline='').read()
               if os.path.exists(OUT) else '')
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\r\n')
        w.writeheader()
        w.writerows(rows)
        # A REFUSAL IS NOT A FAILURE OF THE CHECK. FY2014 and FY2015 print the listing
        # under a layout that states no memberships anywhere, so this reader declines them
        # -- permanently, until somebody reads that layout. Failing `--check` on it makes a
        # check that can never pass, which is a check nobody runs. Staleness is the thing
        # being tested; the refusals are printed above and counted here.
        if buf.getvalue() != cur:
            print('  STALE — run: python3 scripts/extract_personnel.py')
            return 1
        print('  town-personnel.csv is current')
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {os.path.relpath(OUT, ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
