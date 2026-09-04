"""Every budget line the district's documents print, budget and actual, year by year.

`extract_budget_history.py` pulls named groups -- the paras, the buses, the totals. This
pulls EVERYTHING: each row of each table, keyed by the district's own label for it, with
each column mapped to the fiscal year and kind the document states in its own header.

What it is for. The totals say the district lands within half a percent of its budget most
years. That is a statement about the sum, and a sum can be quiet while everything inside it
is loud -- which is exactly what analyses/budget-vs-actual.md claims about FY25. With one
year you cannot tell a line that always misses from a line that missed once. With eight you
can.

Two things this inherits from the group extractor, and both matter:

  * nothing is taken by position. Each document states its columns and the header is read.
  * a fiscal year does not have one budget figure, so the STAGE is recorded and only like
    is compared with like.

And one thing it adds: labels drift. "M.S. Specl Ed Resourse Rm Tchrs" and "M.S. Specl Ed
Resource Rm Teacher" are the same line in different years, so labels are normalised before
matching -- lowercased, punctuation dropped, and the district's own abbreviations folded
together. Where normalisation cannot decide, the line simply does not match across years
and is dropped rather than guessed at.

    python3 scripts/extract_line_history.py
"""
import os, re, csv, sys, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'sources/district-budget/text')
INDEX = os.path.join(ROOT, 'sources/district-budget/index.csv')
OUT = os.path.join(ROOT, 'sources/data/line-history.csv')
COVERAGE = os.path.join(ROOT, 'sources/data/line-history-coverage.csv')
DISAGREE = os.path.join(ROOT, 'sources/data/line-history-disagreements.csv')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'ebh', os.path.join(ROOT, 'scripts/extract_budget_history.py'))
ebh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ebh)

# A data row is a label followed by numbers. Split at the first digit or dollar sign
# rather than matched with one regex: a pattern with a lazy label and a repeating number
# group backtracks catastrophically on the handful of rows that are nearly-but-not-quite
# a data row, and there are six thousand rows to get through.
FIRST_NUM = re.compile(r'[\d$(]')
# A parenthetical belongs to the LINE'S NAME unless it is a bare money amount. The
# district writes "P.S. Teachers/Regular (1-2)", "Athletic Transportation (685)" and
# "H.S. Tech/Industrial Arts Maint. (3D printer)", and splitting the row at that opening
# bracket put "1" and "2" at the front of the numbers and shifted every real figure two
# places along. FY26 for P.S. Teachers/Regular was published as $1,052,440, which is the
# FY24 actual; FY23 and FY24 were published as 1 and 2. A shifted row is the worst kind of
# wrong because the series still looks like a series -- the same failure the group
# extractor's NUM comment describes, arriving by a different door.
#
# What still counts as a value is what MUNIS and Excel print for a negative: a comma-
# grouped amount or one with cents, in brackets, optionally with a dollar sign --
# "(157,886.32)$". "(70% = $422,408)" is neither, and is part of the name it follows.
MONEY_PAREN = re.compile(r'\(\s?\$?\s?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d{2})\s?\)')


def split_row(t):
    """(label, numbers-part) for a data row, or None."""
    pos = 0
    while True:
        m = FIRST_NUM.search(t, pos)
        if not m:
            return None
        if t[m.start()] == '(' and not MONEY_PAREN.match(t, m.start()):
            close = t.find(')', m.start())
            if close == -1:
                # An opening bracket that never closes means the LINE is truncated, not
                # that the figures start here. `fy26-school-dept-approved-budget-3-12-25`
                # line 308 ends mid-number: "Circuit Breaker (70% = $422,408) (75% = 45",
                # and reading it yielded 75 and 45 as the FY25 and FY26 budgets for that
                # line. Both figures were published. A row whose text is cut off is not a
                # row, and the PDF text layer that cut it is part of the finding.
                return None
            if close - m.start() <= 48:
                pos = close + 1        # part of the name; keep looking for the figures
                continue
        break
    if m.start() < 4:
        return None
    start = m.start()
    # A minus TOUCHING the digits is that figure's sign and has to travel with it, or it
    # is left behind in the label and the figure enters positive -- which is how the FY25
    # approved budget's Circuit Breaker offset was counted the wrong way round. A dash
    # with a space after it is the sheet's notation for an empty column, not a sign, and
    # is deliberately left where it is. See signed().
    if start and t[start - 1] == '-' and not (start > 1 and t[start - 2].isdigit()):
        start -= 1
    label = t[:start].strip().rstrip('-').strip()
    if len(label) < 3 or not label[0].isalpha():
        return None
    return label, t[start:]
GROUP_HEADER = re.compile(r'^\d{4}\s*-\s')
# `Page 1 of 10` is a footer, not a budget line, and it appears in 22 of these documents.
# It reads as a label followed by two numbers, which a multi-column layout throws out for
# being too short and a single-column layout accepts as a figure of $1. Ten of them put
# $55 into the FY19 approved budget's extract and helped keep it from tying to its own
# printed total.
SKIP = re.compile(r'^(TOTAL|Total|DESCRIPTION|FY\d|Page\s+\d+(\s+of\s+\d+)?\s*$)', re.I)

# The district's own abbreviations, folded so the same line matches itself across years.
ABBREV = [
    (r'\bspecl\b|\bspecil\b|\bspeci\b|\bspecial\b', 'special'),
    (r'\bed\b|\beduc\b|\beducation\b', 'ed'),
    (r'\btchrs?\b|\bteachers?\b|\bteach\b|\btea\b', 'teacher'),
    (r'\brsourse\b|\bresourse\b|\bresource\b', 'resource'),
    (r'\brm\b|\broom\b', 'rm'),
    (r'\bparaprofessionals?\b|\bparas?\b', 'para'),
    (r'\bpathologists?\b|\bpathigsts\b|\bpathlgsts\b|\bpathologis\b|\bpathologi\b', 'pathologist'),
    (r'\bsubs?\b|\bsubstitutes?\b', 'sub'),
    (r'\bmater\b|\bmaterials?\b', 'materials'),
    (r'\bsupt\b|\bsuperintendent\b', 'supt'),
    (r'\bsvcs?\b|\bservices?\b|\bser\b', 'services'),
    (r'\bcont\b|\bcontracted\b|\bcontrctd\b', 'contracted'),
    (r'\bps\b|\bprimary\b', 'ps'), (r'\bes\b|\belementary\b', 'es'),
    (r'\bms\b|\bmiddle\b', 'ms'), (r'\bhs\b|\bhigh\b', 'hs'),
]


def norm(label):
    """A label reduced to something that matches itself across years.

    Parentheticals go first: the workbook writes "P.S. Teachers/Regular (1-2)" and the
    presentations write "P.S. Teachers/Regular", and those are one line. Then the school
    word is dropped where an abbreviation already carries it -- "Middle School Teachers"
    and "M.S. Teachers" are also one line, and leaving them apart put the three largest
    lines in the budget, $19M of teaching salary, into an unattributed bucket.
    """
    s = label.lower().strip().rstrip('*.')
    s = re.sub(r'\([^)]*\)', ' ', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    # "M.S." loses its dots before the abbreviations are applied and arrives as two
    # tokens, so \bms\b never fires and "M.S. Teachers" never meets "Middle School
    # Teachers". That one gap held $7.4M of teaching salary, four psychologists and the
    # guidance lines out of every function group.
    s = re.sub(r'\b([pemh]) s\b', r'\1s', s)
    for pat, rep in ABBREV:
        s = re.sub(pat, rep, s)
    s = re.sub(r'\b(ps|es|ms|hs) school\b', r'\1', s)
    return re.sub(r'\s+', ' ', s).strip()


def layouts(lines):
    """The column layout in force at every line, computed once per document.

    The group extractor walks backwards from each row to find its header, which is fine
    for six lines and quadratic for six thousand. Here the headers are found once and
    carried forward, which is the same answer and roughly a thousand times less work.

    Returns (per-line layout, header) where header is (line number, the years line, the
    kinds line) for the LAST header this document resolved -- kept so a document that
    yields nothing can say what it was looking at, and so a document that yields plenty
    can be checked against the two lines its whole table rests on.
    """
    out = [None] * len(lines)
    cur, hdr = None, None
    for i, ln in enumerate(lines):
        ys = ebh.YEARS.findall(ln)
        if len(ys) >= 2 and header_is_a_row_of_years(ln):
            got, partial = None, None
            for k in range(i + 1, min(len(lines), i + 3)):
                ms = kinds_in(lines[k])
                ks = [x.group(1).lower() for x in ms]
                if len(ks) >= len(ys):
                    # THE KINDS ROW DECLARES THE WIDTH, even where the years row does not.
                    # `final-fy26-sc-approved-budget-3-12-25` heads two years over eight
                    # columns -- `Actual Budgeted Budgeted Dollar Change % Change Budgeted
                    # Dollar Change % Change` -- because only the first two columns are
                    # labelled with a year. Mapping the two and demanding two numbers let
                    # any row with a dash in it through, shifted: `Dues/Meetings -$
                    # 5,971.00$ 6,500.00$ ...` put 5,971 in FY24 and 6,500 in FY25 when
                    # 5,971 IS the FY25 figure and FY24 is the dash.
                    #
                    # Padding to the full declared width means such a row is short and is
                    # skipped. A skipped row is visible; a shifted one is not, and 133 of
                    # the FY2025 cells the completeness matrix called contested were two
                    # documents shifted this way rather than the town disagreeing with
                    # itself.
                    cols = [None if TO_DATE.match(lines[k][x.end():])
                            else (2000 + int(y), x.group(1).lower(), '')
                            for y, x in zip(ys, ms[:len(ys)])]
                    cols += [None] * (len(ks) - len(ys))
                    got = (cols, lines[k].strip())
                    break
                if partial is None and ks and leading_columns_only(lines[k], ms[0]):
                    partial = (partial_layout(ys, ks, ms, lines[k]),
                               lines[k].strip())
            # Only if the document does NOT put its column kinds on one line. The
            # two-line rule reads 24 documents today and must go on reading them
            # identically, so the wrapped walker is a fallback and never a replacement.
            if got is None:
                got = wrapped_columns(lines, i, ys)
            # And reading only the leading columns is the LAST resort, after both. It
            # fired first once, and the FY27 budget documents went from four columns to
            # one: `DISTRICT EXPENSES FINAL BUDGET` names one kind for four years, which
            # is a partial layout by this test and a wrapped header in fact.
            if got is None:
                got = partial
            if got:
                cur, kindtext = got
                hdr = (i + 1, ln.strip(), kindtext)
        out[i] = cur
    if hdr is None:
        return single_column(lines)
    return out, hdr


def single_column(lines):
    """A budget that prints ONE year, for documents where nothing else resolved.

    The FY25 final approved budget -- the document the School Committee actually voted --
    heads its table `FY25` on one line and `DESCRIPTION, EXPENSES Proposed` on the next.
    341 rows across its two files, and the reader wanted two fiscal years before it would
    read anything, so the year read as absent from the archive while the document sat in
    it. The FY19 approved budget (280 rows) is the same shape.

    Relaxing the bound to one year is genuinely dangerous, which is why it is not what
    this does. A stray `FY25` in a sentence with the word `Budget` under it would set a
    layout for the rest of a file, and then every row's FIRST number -- a page number, a
    date, an account code -- becomes that year's budget for a line. So three guards, and
    all three have to hold:

      * NO line anywhere in the document names two or more fiscal years. Not merely "no
        multi-column header resolved" -- that was the first version of this guard and it
        was far too weak, because a document whose six column kinds are not in the
        vocabulary resolves nothing and would then have been read as though it printed
        one column. `fy19-supt-proposed-expense-budget.txt` heads its table
        `FY14 FY15 FY16 FY17 FY18 FY19 %`; reading its first number as an FY19 budget
        would have published five years of actuals as budgets. A document that prints
        several year columns is not a single-column document even when we cannot parse it.
      * it carries at least twenty of the district's own four-digit function group
        headers -- `1110 - School Committee`. That is what a line-item budget table looks
        like and what a slide deck does not.
      * the year sits at the top of a page, with a column kind on that line or within the
        two below it.

    The per-row guard is in scan(): with one column, a row is only read once a group
    header has been seen, so prose above the first `1110 -` cannot enter the table.
    """
    none = ([None] * len(lines), None)
    if sum(1 for ln in lines if GROUP_HEADER.match(ln.strip())) < 20:
        return none
    if any(len(ebh.YEARS.findall(ln)) >= 2 for ln in lines):
        return none
    out = [None] * len(lines)
    cur, hdr, page = None, None, 0
    for i, ln in enumerate(lines):
        if PAGE.match(ln):
            page = i
        ys = ebh.YEARS.findall(ln)
        if len(ys) == 1 and i - page <= 12:
            for k in range(i, min(len(lines), i + 3)):
                ms = list(kinds_in(lines[k]))
                if ms:
                    cur = [(2000 + int(ys[0]), ms[0].group(1).lower(), '')]
                    hdr = (i + 1, ln.strip(), lines[k].strip())
                    break
        out[i] = cur
    return out, hdr


# The PDF text layer runs two column labels together when the columns are tight:
# `FY19 Superintendent of Schools Recommended Budget` heads its kinds row
# `DESCRIPTION Actual Actual Actual Actual Budgeted Recommendedincrease`, with the sixth
# column's name welded to the seventh's. `\bRecommended\b` then finds no word boundary and
# the row resolves five kinds for six years, so both FY19 superintendent's budgets -- 308
# rows between them -- read as nothing at all. Splitting before a change-column word is
# narrow enough to be safe: `increase`, `decrease` and `difference` are labels for the
# computed column these sheets always carry last, and none is part of a kind's name.
GLUED = re.compile(r'(?<=[A-Za-z])(?=(?:increase|decrease|difference)\b)', re.I)

# Kinds this reader knows and the group extractors deliberately do not.
#
# `Forecast` is the district's own name for the FY27 column in the 16 February 2026
# projection -- `DISTRICT EXPENSES FINAL  FORECAST` over `FY26  FY27` -- and without it
# that document, 256 rows, resolves one kind for two years and reads as nothing.
#
# It is kept OUT of extract_budget_history.py's shared vocabulary on purpose. Adding it
# there let the 16 February forecast win over the 24 February and 23 March documents that
# supersede it, because that extractor still tie-breaks on filename, and it moved FY27
# collaborative tuition from $163,742 to $250,000 -- a projection input, changed as a side
# effect of reading one superseded document. The date-ordering fix belongs there too, but
# it has to be done deliberately with the model re-checked, not sideways.
EXTRA_KINDS = ('Forecast',)
# Built by splicing rather than by re-typing the shared list, so a kind added there is
# picked up here automatically. `ebh.KINDS.pattern` ends `...|Approved)\b`.
LINE_KINDS = re.compile(
    ebh.KINDS.pattern.replace(r')\b', '|' + '|'.join(EXTRA_KINDS) + r')\b'), re.I)
LINE_BUDGET_KINDS = ebh.BUDGET_KINDS | {k.lower() for k in EXTRA_KINDS}


# `Actuals to date` is NOT an actual. It is a year-to-date figure -- what had been spent
# by the day the report was run -- and comparing one to a full-year budget is the error
# rule 1 exists to prevent. The 16 March 2026 projection carries such a column for FY26,
# and reading it as an actual made the whole-budget sweep report FY26 spending 42% under
# budget with three and a half months of the year still to run.
TO_DATE = re.compile(r'^\s*(to\s+date|ytd)\b', re.I)


def kinds_in(text):
    """The column kinds a header line names, with any welded-on change label split off."""
    return list(LINE_KINDS.finditer(GLUED.sub(' ', text)))


def header_is_a_row_of_years(text):
    """A column header is a row of fiscal years. A sentence that mentions one is not.

    Both are matched by "two or more FY tokens on a line", which is how the reader came
    to publish budget lines called `making class sizes approximately` and `not be able to
    oversee sports in all three seasons in grades`, with fiscal years and dollar values,
    out of the FAQ and a community-forum notice. Their "header" was a paragraph.

    Every real column header in this archive carries at most two tokens that are not
    fiscal years -- `Supt. %` is the widest -- and every false one carries four, seven,
    eleven or a hundred and twenty-one. The gap is wide enough to stand on.
    """
    rest = ebh.YEARS.sub(' ', text)
    return len([w for w in rest.split() if w not in ('%', '|')]) <= 2



def declared_width(lines, lay):
    """How many numbers a full row of this document carries: the most common count.

    The header rows cannot be trusted to say how wide the table is.
    `final-fy26-sc-approved-budget-3-12-25` names two fiscal years over eight columns --
    `Actual Budgeted Budgeted Dollar Change % Change Budgeted Dollar Change % Change` --
    because only the first two carry a year. The FY18 sheets put `Increase/Decrease` on
    the years row instead. Counting label words to reconcile the two was tried and is a
    losing game: `% increase` is a percentage whose token is dropped before the row is
    measured and takes up no room, `Dollar Change` prints a number and does, and the two
    halves of the label can sit on different rows.

    The rows themselves say it without being asked. Take the count that occurs most often
    and require it. A document whose full rows carry six numbers has six columns, whatever
    its header managed to print, and a row carrying five is short -- which is the whole
    point, because a short row read against the wrong columns is shifted, and a shifted
    row still looks like a series.

    Never narrower than the years the header names, so this can only ever tighten.
    """
    counts = collections.Counter()
    for i, ln in enumerate(lines):
        t = ln.strip()
        if not t or SKIP.match(t) or GROUP_HEADER.match(t) or not lay[i]:
            continue
        parsed = split_row(t)
        if not parsed:
            continue
        n = len([x for x in ebh.NUM.finditer(parsed[1])
                 if parsed[1][x.end():x.end() + 1] != '%'])
        if n:
            counts[n] += 1
    if not counts:
        return 0
    return max(counts.most_common(1)[0][0], max(len(c) for c in lay if c))


def leading_columns_only(text, first):
    """Whether the first kind this line names can be trusted to be its first column.

    The Town Manager's own budget sheets head five year columns
    `FY25 FY26 FY26 FY26 FY26 %` over
    `Budgeted Level Adj Needs Based TM 030525 TM 031225 increase`. Four of the five column
    names are scenario labels -- the dates are the days the Town Manager published each
    version -- and no rule segments `Level Adj Needs Based` into two labels without knowing
    in advance that it is two. So the document cannot be read column by column.

    It can be read for the columns it DOES name. `Budgeted` is column one, and reading
    only that yields the FY25 budget for 322 lines out of a 356-row document that was
    otherwise unread entirely.

    The guard is that the named kind really is the first column and not the third: at most
    three whitespace tokens may precede it, which admits the table captions these sheets
    use -- `DESCRIPTION`, `DESCRIPTION, EXPENSES`, `DISTRICT EXPENSES` -- and not two
    unnamed columns. The row-length check in scan() does the rest: a row must still carry
    as many numbers as there are YEARS, so the positions are known even where the names
    are not.

    Checked, not assumed. The 322 rows read this way from the 12 March 2025 sheet agree to
    the dollar with all 319 they share with the approved budget the district published the
    same day.
    """
    return len(text[:first.start()].split()) <= 3


def partial_layout(ys, ks, ms=None, text=''):
    """Columns for the kinds we can name, and None for the ones we cannot.

    The list is as long as the years, so `len(nums) < len(cols)` still requires a full
    row -- the positions have to be certain even though the names are not. scan() skips
    the None entries; nothing is guessed for them and the coverage row says so.
    """
    def col(i, y):
        if i >= len(ks):
            return None
        if ms and TO_DATE.match(text[ms[i].end():]):
            return None               # a year-to-date column is not an actual
        return (2000 + int(y), ks[i], '')
    return [col(i, y) for i, y in enumerate(ys)]


def wrapped_columns(lines, j, ys):
    """The column layout when the kinds row is broken over several lines.

    `fy27-budget-projections-as-of-2-24-26` prints its eleven column kinds on one line and
    reads fine. The 3/16/26 and 3/23/26 documents that supersede it are the same table
    from a different PDF pass, with each column's name split across two lines:

        5: FY26  FY27  FY27  FY27  FY27
        6: DISTRICT EXPENSES FINAL BUDGET
        7:  Restoration
        8: Proposed
        9:  Core Budget
       10: Proposed

    Both were unreadable, so every FY27 figure the site publishes comes from February and
    the March documents that replaced it sat unread.

    A line CLOSES a column when what remains of it after its kind words are removed is
    empty -- `Proposed` closes, `Core Budget` does not, which is the whole difficulty,
    since Budget is a kind word and Core Budget is a scenario name. The first line under
    the years row always closes, because it carries the table's caption alongside the
    first column's kind. Kindless lines accumulate as the NEXT column's variant: the
    document's own name for that scenario, kept verbatim.

    Returns None unless it resolves EXACTLY as many columns as there are years. That is
    the only thing standing between this and a shifted row, which is a silent corruption
    -- the series still looks like a series. The 3/16/26 document resolves ten columns for
    eleven years, because `Encumbrances to date` names no kind at all, and is refused.
    """
    cols, pending, kindtext = [], [], []
    for k in range(j + 1, min(len(lines), j + 14)):
        t = lines[k].strip()
        if not t:
            continue
        if GROUP_HEADER.match(t) or len(ebh.YEARS.findall(t)) >= 2:
            break
        ms = list(kinds_in(t))
        if ms and (k == j + 1 or not ebh.KINDS.sub('', GLUED.sub(' ', t)).strip()):
            kindtext.append(t)
            for n, m in enumerate(ms):
                cols.append((m.group(1).lower(), ' '.join(pending) if n == 0 else ''))
                pending = []
        elif split_row(t):
            break                       # a data row: the header is over
        else:
            pending.append(t)
        if len(cols) > len(ys):
            return None
    if len(cols) != len(ys):
        return None
    return ([(2000 + int(y), kind, variant)
             for y, (kind, variant) in zip(ys, cols)],
            ' | '.join(kindtext))


PAGE = re.compile(r'^===(PAGE|SHEET)')
# The widest column header any document in this archive actually resolved is SIX fiscal
# years -- FY14 through FY19, in the six FY19 hearing documents. A line naming eight or
# fourteen of them is a history chart on a slide, and slides are short enough that every
# line on one sits near a page break, so the page-top test alone does not separate them.
# Without this the matrix claimed the archive holds a line-level FY2010 budget document,
# on the strength of one axis label. That is the same over-claim as reporting the year
# absent, pointed the other way.
WIDEST_REAL_HEADER = 7


def year_candidates(lines):
    """Lines that look like a row of fiscal years, whether or not a layout came of one.

    A document whose header was not understood is the interesting case, and the only way
    to tell it apart from a document that has no table is to record what it does have.

    Each candidate carries whether it sits at the TOP OF A PAGE, and that flag is what
    decides which fiscal years a document may be said to cover. A table header is printed
    at the top of the page it heads. A line reading `FY10 FY11 ... FY23` two thirds of the
    way down a slide deck is a chart of enrolment or levy history, and treating it as a
    header would have the coverage matrix claim the archive holds line-level budget
    documents for FY2010 -- turning one over-claim (a year absent that is not) into
    another (a year held that is not). Neither is worth having.
    """
    page = 0
    out = []
    for i, ln in enumerate(lines):
        if PAGE.match(ln):
            page = i
        n = len(ebh.YEARS.findall(ln))
        if n >= 1:
            out.append((i + 1, ln.strip(), n, i - page <= 12))
    return out


MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun',
          'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
DATE = re.compile(
    r'(?<!\d)(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})(?!\d)'
    r'|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b',
    re.I)


def parse_date(text):
    """(y, m, d) from the first date in `text`, or None. m/d/yy as the district writes it."""
    m = DATE.search(text or '')
    if not m:
        return None
    if m.group(1):
        mm, dd, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if yy < 100:
            yy += 2000
    else:
        mm = MONTHS.index(m.group(4)[:3].lower()) + 1
        dd, yy = int(m.group(5)), int(m.group(6))
    return (yy, mm, dd) if 1 <= mm <= 12 and 1 <= dd <= 31 else None


def publisher_labels():
    """The district's own title for each mirrored file, from the archive index.

    Used only for its DATE. The label is the publisher's own name for the document --
    rule 12 keeps it for exactly this reason -- so a date inside it is the publisher
    speaking, not our filename convention.
    """
    out = {}
    if os.path.exists(INDEX):
        with open(INDEX, encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                if r.get('text'):
                    out[os.path.basename(r['text'])] = r.get('label', '')
    return out


def document_date(path, lines, labels):
    """When the publisher says this document was written, or None.

    Two documents about the same fiscal year are ordered by this, and where neither
    states a date the order falls back to the filename -- stated here rather than left
    to whatever `sorted(glob)` happens to do. See the collapse in main() for why that
    tiebreak decides 135 published figures.
    """
    return (parse_date(labels.get(os.path.basename(path)))
            or parse_date(' '.join(lines[:8])))


def why_no_header(lines, widest, data_rows):
    """Which of the three shapes this unread document is, quoted from its own header.

    A list of documents the reader could not read is a complaint. A list saying WHICH of
    three things is wrong with each is a work queue, and the three want different fixes:

      one year only     the FY25 approved budget prints a single column. Reading it means
                        accepting a one-year header, which is a real risk -- a stray FY25
                        in a sentence followed by the word Budget would set a layout for
                        the rest of the file -- so it needs a guard, not a loosened bound.
      kinds wrapped     the same table, extracted by a different PDF pass, with the column
                        kinds broken over six lines instead of one. The 3/23/26 FY27
                        budget fails this way while the 2/24/26 one does not, so the site
                        quotes February for a document March superseded.
      kinds unknown     the column is named for a scenario -- "Needs Based", "TM 031225" --
                        and there are four of them for one fiscal year. Reading those means
                        deciding what a stage is, which is a question and not a parser bug.
    """
    if not widest:
        return 'no fiscal year stated anywhere: %d row(s) of data' % data_rows
    n, text, ny, _ = widest
    if ny < 2:
        return ('single-column table: line %d states one fiscal year, %r, and this reader '
                'requires two' % (n, text))
    below = ' | '.join(l.strip() for l in lines[n:n + 8] if l.strip())
    ks = [m.group(1) for m in kinds_in(below)]
    if len(ks) >= ny:
        return ('header wrapped: line %d states %d fiscal years, %r, and the column kinds '
                'run past the two lines below it -- %s' % (n, ny, text, ' / '.join(ks)))
    return ('column kinds not in the vocabulary: line %d states %d fiscal years, %r, and '
            'the lines below name %s' % (n, ny, text, ' / '.join(ks) or 'none of them'))


PRINTED_TOTAL = re.compile(r'^TOTAL\s+(BUDGET|SALARIES|EXPENSES)\s*:?\s*'
                           r'\$?\s?(\d{1,3}(?:,\d{3})+|\d+)', re.I)


def printed_totals(lines):
    """Every TOTAL the document prints for itself, by name.

    `TOTAL EXPENSES: 7,695,034` on the last page of the FY25 approved budget. Rule 13:
    when an extract has a total the source itself prints, reconcile to it.
    """
    out = {}
    for ln in lines:
        m = PRINTED_TOTAL.match(ln.strip())
        if m:
            out.setdefault(m.group(1).upper(), ebh.money(m.group(2)))
    if 'SALARIES' in out and 'EXPENSES' in out:
        out['SALARIES+EXPENSES'] = out['SALARIES'] + out['EXPENSES']
    return out


def ties_to_a_printed_total(values, lines):
    """(the total it ties to, the difference) for a single-column extract, or None.

    **A single-column document is not loaded unless it ties.** With one column every row
    contributes its first number, so the ordinary defences -- more numbers than columns,
    a kinds row to align against -- are all absent, and a page of prose under a stray
    heading reads exactly like a budget. Three of the first six documents this reader
    accepted summed to $777, $55 and $66 across forty-odd "figures". Nothing about the
    shape of the text said so; only the total did.

    The tolerance is a dollar a row -- this project's standing convention for columns a
    source prints rounded, notes/reference/SCHEMA.md -- or a quarter of one percent, whichever is
    larger. It passes the FY25 approved budget, whose expense lines come to $9 over the
    $7,695,034 the document prints at the foot of its own page.

    The quarter of a percent is there for the FY19 approved budget, which is out by
    $4,190 on $20,190,110 -- 0.02% -- because **the document's own TOTAL EXPENSES omits
    one of two `Curriculum Adoption/System` rows it prints**, at $17,686. The extract is
    right and the printed total is the thing that does not add up. It is not for us to
    decide which of the two rows the district meant, so the row stays in and the
    difference is reported in the coverage file rather than hidden by it. What settles
    that the read is sound is a second document: 219 of the 246 FY19 lines it shares with
    the FY20 budget hearing document agree to the dollar, and a misaligned column would
    have disagreed on all of them.

    The loosening is safe because it is not what refuses the bad documents. Those are
    refused for printing no total at all.
    """
    if not values:
        return None
    total = sum(values)
    tol = max(len(values), 5.0)
    best = None
    for name, want in printed_totals(lines).items():
        d = abs(total - want)
        if best is None or d < best[1]:
            best = (name, d, max(tol, abs(want) * 0.0025))
    if best and best[1] <= best[2]:
        return best[:2]
    return None


def signed(rest, match):
    """The value at `match`, negated if the document printed it as a negative.

    Two notations, both the district's own:

        Circuit Breaker (70% = $422,408) (75% = 452,580)-452,580
        School Committee Conference Exp -   (250.00)$

    A minus IMMEDIATELY before the digits, or brackets around them. The adjacency matters:
    these sheets also use a lone dash for zero, and `18,000 - 8,444` is two positive
    figures with an empty column between them, not a subtraction. A dash with a space
    after it is the empty column; a dash touching the digits is a sign.

    This was worth finding. The FY25 approved budget's expense lines summed to $8,600,203
    against the $7,695,034 the document prints at the bottom of its own page, and the
    entire $905,169 gap was the Circuit Breaker offset counted once with the wrong sign
    and therefore twice in the total. Reading it as printed makes the extract tie.
    """
    v = ebh.money(match.group(1))
    tok = match.group(0)
    before = rest[max(0, match.start() - 1):match.start()]
    if tok.startswith('(') or before == '-':
        return -v
    return v


def scan(path, labels=None):
    """Every figure this document states, plus WHY it stated none where it states none.

    The second return value is the point. 61 of the 85 documents on the district's budget
    page came through this reader with nothing at all, and because the reader only ever
    printed what it found, the archive looked like it did not hold FY25's approved budget
    when what had actually happened is that the approved budget prints ONE year column and
    this reader required two. A coverage matrix built on the output then reported an
    extraction gap as an acquisition gap -- and would have asked the Superintendent for
    ten documents already on disk.

    So every document returns a diagnosis whether or not it returns figures, and `main`
    writes all 85 of them out. Same rule as search_minutes.py: print the denominator,
    because a reader that finds nothing prints nothing and nothing reads as absence.
    """
    raw = open(path, encoding='utf-8', errors='replace').read()
    lines = raw.split('\n')
    dy = ebh.document_year(lines)
    dd = document_date(path, lines, labels or {})
    lay, hdr = layouts(lines)
    # Pad every layout out to the width the document's own rows show it to have, with
    # None for the columns the header did not name. scan() skips None; the row-length
    # check does not, which is the point -- see declared_width().
    width = declared_width(lines, lay)
    lay = [c if not c else c + [None] * max(0, width - len(c)) for c in lay]
    data_rows = with_layout = short_rows = 0
    out, seen_group = [], False
    groups = sum(1 for ln in lines if GROUP_HEADER.match(ln.strip()))
    uses_groups = groups >= 20
    for i, ln in enumerate(lines):
        t = ln.strip()
        if GROUP_HEADER.match(t):
            seen_group = True
            continue
        if not t or SKIP.match(t):
            continue
        parsed = split_row(t)
        if not parsed:
            continue
        data_rows += 1
        label, rest = parsed
        cols = lay[i]
        if not cols:
            continue
        # A BUDGET LINE LIVES UNDER A FUNCTION GROUP HEADER -- in the documents that use
        # them. The district prints `1110 - School Committee` over each block of lines and
        # 349 of 351 lines in the workbook sit under one, so in those documents a row that
        # has not yet passed a header is the prose or the summary table above the table.
        #
        # Not all of them use one. The FY19 per-department budgets -- athletics,
        # maintenance, health -- are single-department documents that head their sections
        # `EXPENSES` and `Athletic Personnel` and carry no four-digit code anywhere.
        # Requiring a header of every document dropped all six, and with them `Athletic
        # Officials`, `H.S. Library Para` and `GRAND TOTAL ATHLETICS` for FY14-FY19. So
        # the rule applies where the convention does, and the header line itself carries
        # the weight elsewhere -- see header_is_a_row_of_years().
        if uses_groups and not seen_group:
            continue
        with_layout += 1
        # A percentage is not a dollar. Every one of these sheets carries a trailing
        # "% increase" column, and on a row that prints a dash for zero the percentage
        # slid forward into a money column: `Kindergarten Paraprofessionals 0 -100.00%`
        # was read as an FY26 budget of 100. Reading the sign made it -100, which is what
        # made it visible; dropping the token is what makes it right, and it also drops
        # the row, because two columns now have one number and a short row is skipped.
        nums = [signed(rest, x) for x in ebh.NUM.finditer(rest)
                if rest[x.end():x.end() + 1] != '%']
        if len(nums) < len(cols):
            short_rows += 1
            continue
        for col, v in zip(cols, nums[:len(cols)]):
            if col is None:
                continue                  # a column the document names in a way we cannot read
            fy, kind, variant = col
            if kind in LINE_BUDGET_KINDS:
                stage = ebh.stage_of(fy, kind, dy)
            elif kind in ebh.ACTUAL_KINDS:
                stage = 'actual'
            else:
                continue
            out.append(dict(fy=fy, label=label, key=norm(label), stage=stage, value=v,
                            variant=variant, doc=os.path.basename(path), docYear=dy,
                            docDate=dd))

    # AN ENROLMENT TABLE IS THE SAME SHAPE AS A BUDGET TABLE. `FY18 FY19 FY20` over
    # `Actual Budgeted Proposed`, one row per school, and the only thing separating the
    # two is what the numbers are. The FY20 recommended-budget presentation carries one,
    # and it produced budget lines called `Lunenburg High School:`, `THES. K`, `grade`
    # and `denominators` with dollar values of 12, 8 and 5.
    #
    # The gap is enormous and does not need a clever test. The median figure in that
    # table is 9. The median in the smallest real budget document in this archive is
    # 1,750, and its total is 45,525 against the presentation's 4,381. A hundred dollars
    # sits two orders of magnitude clear of both.
    reason_median = None
    if out:
        vals = sorted(abs(o['value']) for o in out)
        med = vals[len(vals) // 2]
        if med < 100:
            reason_median = (
                'REFUSED as not a budget table: %d figures with a median of %s and a '
                'total of %s -- an enrolment or class-size table, not dollars'
                % (len(out), format(med, ',.0f'),
                   format(sum(vals), ',.0f')))
            out = []

    # A single-column read is provisional until it meets the document's own total.
    reason_tie = tied_to = None
    if out and any(c and len(c) == 1 for c in lay):
        tie = ties_to_a_printed_total([o['value'] for o in out], lines)
        if tie:
            tied_to = 'ties to the document\u2019s own TOTAL %s, %+.0f over %d rows' % (
                tie[0], tie[1], len(out))
        else:
            totals = printed_totals(lines)
            reason_tie = (
                'single-column extract REFUSED: %d figures summing to %s against the '
                'document\u2019s own %s' % (
                    len(out), format(sum(o['value'] for o in out), ',.0f'),
                    ', '.join('TOTAL %s %s' % (k, format(v, ',.0f'))
                              for k, v in sorted(totals.items()))
                    or 'no printed total at all'))
            out = []

    cands = year_candidates(lines)
    widest = max(cands, key=lambda c: c[2]) if cands else None
    # Only a page-top header may say what years a document covers -- see year_candidates.
    tops = [c for c in cands if c[3] and c[2] <= WIDEST_REAL_HEADER]
    covers = sorted({2000 + int(y) for _, t, _, _ in tops
                     for y in ebh.YEARS.findall(t)} | ({dy} if dy else set()))
    if out:
        reason = tied_to or ''
    elif lines and lines[0].startswith('===SHEET'):
        reason = 'spreadsheet layout (===SHEET, comma separated) -- this reader reads PDF text'
    elif groups >= 20 and data_rows < groups:
        reason = ('the PDF text layer is COLUMN-MAJOR: %d function group headers and only '
                  '%d rows carrying a label and its figures. Labels and numbers came out '
                  'in separate runs -- needs re-extraction with coordinates, not a header '
                  'rule' % (groups, data_rows))
    elif reason_median:
        reason = reason_median
    elif reason_tie:
        reason = reason_tie
    elif lines and lines[0].startswith('===SHEET'):
        # A converted spreadsheet: comma separated, the label in the second field, so
        # split_row never sees a label at the start of the line. A different shape, not a
        # missing document, and it needs its own reader rather than a loosened one here.
        reason = 'spreadsheet layout (===SHEET, comma separated) -- this reader reads PDF text'
    elif groups >= 20 and data_rows < groups:
        # The document IS a line-item budget -- it carries the district's own function
        # group headers, dozens of them -- but its PDF text layer came out COLUMN-MAJOR:
        # the labels in one run and the figures in another, so no single line holds both.
        #
        #     H.S. Repair Science Equip
        #     H.S. Tech/Industrial Arts Maint. (3D printer)
        #     ...
        #     21,200
        #     1,850
        #
        # No header rule fixes that. It needs re-extracting from the PDF with coordinates,
        # which is a different instrument, and saying so is more useful than calling the
        # document unparseable.
        reason = ('the PDF text layer is COLUMN-MAJOR: %d function group headers and only '
                  '%d rows carrying a label and its figures. Labels and numbers came out '
                  'in separate runs -- needs re-extraction with coordinates, not a header '
                  'rule' % (groups, data_rows))
    elif data_rows == 0:
        reason = 'no rows of the shape "label then numbers"'
    elif with_layout == 0:
        reason = why_no_header(lines, widest, data_rows)
    elif short_rows:
        reason = ('every row shorter than its %d columns -- a dash for zero is not read '
                  'as a number, by design' % len(lay[0] or ()))
    else:
        reason = 'columns understood but no column named a budget or an actual kind'

    diag = dict(document=os.path.basename(path), doc_year=dy or '',
                data_rows=data_rows, rows_with_layout=with_layout,
                rows_short_of_columns=short_rows, figures=len(out),
                header_line=hdr[0] if hdr else '',
                header_years=hdr[1] if hdr else (widest[1] if widest else ''),
                header_kinds=hdr[2] if hdr else '',
                doc_date='%04d-%02d-%02d' % dd if dd else '',
                covers=' '.join('FY%d' % y for y in covers),
                reason=reason)
    return out, diag


def main():
    obs, diags = [], []
    labels = publisher_labels()
    for path in sorted(glob.glob(os.path.join(TEXT, '*.txt'))):
        o, d = scan(path, labels)
        obs += o
        diags.append(d)
    read = sum(1 for d in diags if d['figures'])
    print(f'{len(obs):,} observations from {read} of {len(diags)} documents')

    with open(COVERAGE, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(diags[0]))
        w.writeheader()
        w.writerows(diags)
    print(f'wrote {COVERAGE}')

    # The documents that carry a table this reader could not read. Printed every run,
    # loudest first, because this is the number that decides whether a gap in the
    # coverage matrix is a document the town has not given us or a document we have not
    # read. They are not the same thing and they were reported as one.
    unread = sorted((d for d in diags if not d['figures'] and d['data_rows'] >= 20),
                    key=lambda d: -d['data_rows'])
    if unread:
        print(f'\n{len(unread)} document(s) hold 20+ rows of figures and yielded NOTHING:')
        for d in unread:
            print('   %-70s %4d rows  %s' % (d['document'], d['data_rows'], d['reason']))
        print('   These are held, not missing. Coverage must not report them as absent.')

    # Collapse to one figure per (line, year, stage): later documents win, and a
    # disagreement is recorded rather than averaged away.
    # The VARIANT is part of the key. A document that prints four FY27 columns --
    # Restoration Proposed, Core Budget Proposed, Level Service Proposed, Balanced
    # Proposed -- is stating four different figures, and collapsing them onto one key
    # would keep whichever happened to be read last while marking the other three as a
    # disagreement between documents. They are not a disagreement. They are scenarios,
    # and the document names each one.
    #
    # The order is (year the document is about, date the publisher put on it, filename),
    # and the last one wins. The first was the only key here, and Python's sort is STABLE
    # -- so two documents about the same year tie-broke on filename, alphabetically, and
    # 135 published figures were decided by what a file happened to be called. Renaming
    # one would have changed a number on the site.
    #
    # The date comes from the district's own title for the document or its own title
    # block, never from our slug. 60 of 87 documents state one; the rest still fall back
    # to the filename, which is at least now a stated rule rather than an accident.
    best, disagree, stated = {}, set(), collections.defaultdict(list)
    for o in sorted(obs, key=lambda x: ((x['docYear'] or 0),
                                        x['docDate'] or ((x['docYear'] or 0), 1, 1),
                                        x['doc'])):
        k = (o['key'], o['fy'], o['stage'], o['variant'])
        if k in best and abs(best[k]['value'] - o['value']) > 1:
            disagree.add(k)
        best[k] = o
        stated[k].append(o)

    # A budget line is not negative. Every one of these is either a genuine offset the
    # document prints as a credit -- Circuit Breaker, the ACE paraprofessional
    # reimbursement -- or a trailing "Increase/Decrease" column that slid into a money
    # column on a row where one figure was printed as a dash. The two are not separable
    # from the text, so they are counted and named on every run rather than guessed at
    # or quietly dropped. 17 of 21,513 at the time of writing.
    neg = [o for o in best.values() if o['value'] < 0]
    if neg:
        print(f'\n{len(neg)} figure(s) come out NEGATIVE. A budget line is not negative:')
        for o in sorted(neg, key=lambda x: x['value']):
            print('   %-38s FY%d %-9s %12s  %s'
                  % (o['label'][:37], o['fy'], o['stage'],
                     format(o['value'], ',.0f'), o['doc']))
        print('   Offsets are real; the rest are a change column on a short row.')

    keys = sorted({k[0] for k in best})
    print(f'\n{len(keys):,} distinct lines after normalising labels')
    print(f'{len(disagree):,} (line, year, stage) cells where documents disagree')

    with open(OUT, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['key', 'label', 'fy', 'stage', 'variant', 'value',
                    'documents_disagree', 'source'])
        for (key, fy, stage, variant), o in sorted(best.items()):
            w.writerow([key, o['label'], fy, stage, variant, f"{o['value']:.0f}",
                        int((key, fy, stage, variant) in disagree), o['doc']])
    print(f'wrote {OUT}')

    # EVERY DOCUMENT'S FIGURE FOR A CONTESTED CELL, not just the one that wins.
    #
    # `documents_disagree` has always been a flag, and a flag is the least a reader can be
    # told: the completeness matrix says a year is `partial` and cannot say whether that
    # means one line out of 282 or a third of the year. Worse, the losing figure and the
    # document that stated it were thrown away at this exact line, so nothing downstream
    # could show the disagreement even if it wanted to -- the cell could name the winner
    # and no more.
    #
    # This keeps all of them, marks which one the ordering chose, and says nothing about
    # which is right. Two documents stating a line differently is a fact about the
    # documents. Deciding between them is not something this file may do.
    with open(DISAGREE, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['key', 'label', 'fy', 'stage', 'variant', 'source', 'value',
                    'is_kept', 'spread', 'kind'])
        rows_out = 0
        for k in sorted(disagree):
            obs_k = stated[k]
            vals = [o['value'] for o in obs_k]
            spread = max(vals) - min(vals)
            # TWO DOCUMENTS DISAGREEING AND ONE DOCUMENT NAMING TWO LINES THE SAME ARE
            # NOT THE SAME FACT. `Dues/Meetings` appears under School Committee, the
            # Superintendent's Office and the Business Office; `Curriculum Adoption/System`
            # twice on consecutive lines. Normalising the printed name collapses them, and
            # the cell then reports a disagreement that no document is having -- it is
            # ours. Saying which kind it is costs one column and stops a reader chasing a
            # dispute between documents that agree.
            kind = ('same-document' if len({o['doc'] for o in obs_k}) == 1
                    else 'documents')
            for o in sorted(obs_k, key=lambda x: (x['doc'], -x['value'])):
                w.writerow([k[0], o['label'], k[1], k[2], k[3], o['doc'],
                            '%.0f' % o['value'],
                            int(o is best[k]), '%.0f' % spread, kind])
                rows_out += 1
    print(f'wrote {DISAGREE} -- {rows_out:,} statements across '
          f'{len(disagree):,} contested cells')

    pairs = [(k, fy) for (k, fy, st, va) in best if st == 'actual' and not va
             and (k, fy, 'settled', '') in best]
    print(f'{len(pairs):,} line-years with both a settled budget and an actual')
    yrs = collections.Counter(fy for _, fy in pairs)
    print('   by year: ' + ', '.join(f'FY{fy%100} {n}' for fy, n in sorted(yrs.items())))


if __name__ == '__main__':
    main()
