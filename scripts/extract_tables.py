#!/usr/bin/env python3
"""Extract any catalogued table family from the annual town reports, generically.

Twelve datasets remain after receipts, rosters, placements and special revenue, and they
are all the same shape: a label and some money columns, grouped under department headings,
usually ending in a printed total. Writing twelve bespoke extractors would mean making the
same four mistakes twelve times -- and this project has already made each of them twice.

So the rules learned the hard way live here once:

**Position is the data.** Values are keyed to the column ruler, never compacted and never
trimmed. A fund with a blank first column must not have its second column slide left. Two
earlier versions of the special revenue extractor got this wrong in two different ways and
both produced sums 40-60% short, consistently, in every year -- which is what a shift looks
like and what lost rows do not.

**Compare on squashed labels.** The text layer splits words apart -- `GRAND T OT AL`,
`SUMMARY OF RECEIPT S`, `studen ts` -- so an exact string match silently fails. That cost
$119,723,580.93 against a printed $40,193,021.76 once already.

**Locate from the catalogue, never from a heading.** Fifteen years of different town
managers; nothing is called the same thing twice. And match exclusions against a table's
NAME and PRINTED HEADING only, never its description, which mentions half the book.

**A total row is per column.** Reconcile column by column, and report the gap per column
rather than a pass/fail, because a year whose opening balance ties and whose receipts do
not is two different facts.

Anything that does not reconcile is written with `status=partial` and its residuals. The
rows are real; what is missing is the proof.

    python3 scripts/extract_tables.py <dataset> [--list]
"""

import argparse
import collections
import csv
import itertools
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T
import report_pages as RP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, 'sources', 'data', 'extraction-plan.csv')
OUTDIR = os.path.join(ROOT, 'sources', 'data')

GROUP_WORDS = (r'GENERAL GOVERNMENT|SCHOOL|PUBLIC SAFETY|HIGHWAY|PARKS|LIBRARY|HEALTH|'
               r'COUNCIL ON AGING|CULTURE|RECREATION|CEMETERY|SEWER|WATER|VETERANS|'
               r'CONSERVATION|PLANNING|TOWN CLERK|FIRE|POLICE|DPW|EDUCATION|'
               r'DEBT SERVICE|UNCLASSIFIED|INSURANCE|ASSESSOR|TREASURER|SELECTMEN')
GROUP = re.compile(r'^\s*(' + GROUP_WORDS + r')\b.{0,40}$', re.I)

# Datasets that TALLY rather than cost. Their figures are bare integers -- votes,
# headcounts, births -- so the ruler has to be built from integers or it never forms and
# the table is skipped in silence.
COUNT_DATASETS = {'elections', 'enrollment_mcas', 'vital_records', 'dept_activity',
                  'officials'}


def squash(s):
    return re.sub(r'[^A-Z0-9]', '', (s or '').upper())


def is_total(label):
    # `Subtotal Police` and `Subtotal Fire Dept.` are subtotals. Matching only TOTAL left
    # them classed as detail and added to the very lines they summarise, putting the
    # FY2016 omnibus $2.8M over its own printed Total Omnibus.
    return squash(label).startswith(('TOTAL', 'GRANDTOTAL', 'SUBTOTAL'))


def is_grand(label):
    # The omnibus budget's own grand total is called `Total Omnibus`, in nine of the years
    # that print one. Read as an ordinary subtotal it left every omnibus run reporting
    # `no total printed` while the total sat in the table, which is the difference between
    # a run that cannot be checked and one that simply was not.
    return squash(label).startswith(('GRANDTOTAL', 'TOTALOMNIBUS', 'OMNIBUSTOTAL'))


COLUMN_HEADING = re.compile(r'^LINE#?N?O?\.?ACCOUNT')


def is_column_heading(label):
    """`LINE #   ACCOUNT   Fiscal Year 2016` is the table's heading, not a line of it.

    Read as a row it appropriated the year: 2,016 dollars under the heading `LINE #`."""
    return bool(COLUMN_HEADING.match(squash(label)))


def plan_for(dataset):
    """Page ranges per edition, from the catalogue-derived plan."""
    want = collections.defaultdict(set)
    for r in csv.DictReader(open(PLAN)):
        if r['dataset'] != dataset:
            continue
        for a, b in re.findall(r'(\d+)\s*[-–]\s*(\d+)', r['pages'] or ''):
            if int(b) >= int(a) and int(b) - int(a) < 25:
                want[r['edition']].update(range(int(a), int(b) + 1))
        for n in re.findall(r'(?<![\d-])(\d{1,3})(?![\d-])', r['pages'] or ''):
            want[r['edition']].add(int(n))
    return {k: sorted(v) for k, v in want.items()}


def panels(lines, ruler, num=None, counts=False):
    """Split a page's columns into independent PANELS.

    Many of these pages print two or three separate lists side by side — a wage list with
    A–L on the left and L–Z on the right, a receipts page in three columns, the assessors'
    history. Each panel is its own table; a printed line holds one row of EACH.

    Reading across the line instead pairs a left-panel label with a right-panel figure.
    On the FY2025 wage list that deleted every right-hand person and filed their wage under
    a stranger's surname:

        extract:  ABRAHAM  v1=64696.14  v2=2056.23
        page:     ABRAHAM DAVID $64,696.14   |   LEGER VICTORIA $2,056.23

    Every figure was real and every pairing was false — which is worse than a missing row,
    because a missing row shifts nothing while this asserts something untrue.

    A panel is found by structure: a label column followed by its money columns, repeating.
    Returns a list of (label_index, [value_indices]).
    """
    num = num or T.amount
    figures = T.figure_rows(lines, counts)
    if not figures:
        return []
    width = max(len(T.cells(f, ruler)) for f in figures)
    kind = []
    for i in range(width):
        money = text = 0
        for f in figures:
            c = T.cells(f, ruler)
            if i >= len(c) or not c[i].strip():
                continue
            if num(c[i]) is not None:
                money += 1
            elif re.search(r'[A-Za-z]{2}', c[i]):
                text += 1
        kind.append('money' if money > text else 'text' if text else '')

    # Consecutive text columns are ONE label, not two panels.
    #
    # The wage lists print surname and forename in separate columns
    # (`ABRAHAM | DAVID | $64,696.14`), so treating every text column as the start of a
    # panel made the label the forename and threw the surname away — 98 rows all named
    # `DAVID`, `VICTORIA`, `BRIANA`. A panel begins at a text column only when a money
    # column has been seen since the last one.
    out, label, vals = [], None, []
    for i, k in enumerate(kind):
        if k == 'text':
            if label is not None and vals:
                out.append((label, vals))
                label, vals = i, []
            elif label is None:
                label, vals = i, []
            else:
                label = (label if isinstance(label, list) else [label]) + [i]
        elif k == 'money' and label is not None:
            vals.append(i)
    if label is not None and vals:
        out.append((label, vals))
    # A single label with all the money after it is the ordinary one-panel table.
    return out or []


TRAILING = re.compile(r'^(.*?[A-Za-z].*?)((?:\s+\(?-?[\d][\d,]*\.?\d*\)?){2,})\s*$')


def trailing_numbers(lines, num):
    """Read a table as `label  n  n  n  n` — the trailing figures ARE the columns.

    For a tally table this is more faithful than the column ruler, and the FY2016 election
    page shows why. Its OCR has geometry and no digits: Vision never recognised the
    standalone `0` glyphs, so `** Dennis Mannone  6  0  0  11  17` came through as
    `6 … 11 17`, and the bottom half of the page returned no figures at all. The text layer
    has every digit and no column positions.

    Neither rendering is usable alone. But a row of vote counts does not need positions:
    the figures run to the end of the line, in order, and the label is what precedes them.
    Reading it that way recovers the page from the text layer and keeps the printed zeros
    that the geometry lost.

    Returns [(label, [values])] or [] when the page is not this shape.
    """
    out = []
    for line in lines:
        m = TRAILING.match(line.rstrip())
        if not m:
            continue
        label = m.group(1).strip()
        vals = [num(v) for v in m.group(2).split()]
        if label and any(v is not None for v in vals):
            out.append((label, vals))
    return out



def money_columns(lines, ruler, num=None, counts=False):
    """Cell indices that hold a figure in a fair share of this page's figure-bearing rows.

    Computed per page and applied to every row, so a blank stays a blank in its own column.
    """
    num = num or T.amount
    figures = T.figure_rows(lines, counts)
    hits = collections.Counter()
    for f in figures:
        for i, c in enumerate(T.cells(f, ruler)):
            if T.amount(c) is not None:
                hits[i] += 1
    need = max(1, len(figures) // 5)
    return sorted(i for i, n in hits.items() if n >= need), len(figures)


# The ruler's blank-fraction is not a constant. It is a property of the page.
#
# `column_ruler` calls a position a gutter when it is blank in 92% of rows, and that one
# number decides how much of a page is readable. FY2011 page 64 prints 98 money tokens and
# yielded 26 of them: two columns an eighth of an inch apart never reached 92% agreement,
# so they merged into one cell holding `$83,989.21       $83,989.21`, which parses as
# nothing at all. Nothing reported this. The page contributed a quarter of its money to the
# year's total and the year still reconciled to within 1%, by cancellation.
#
# So the threshold is SEARCHED, per page, against a measurable objective: how many of the
# money tokens the page prints end up inside a column. Ties go to the ruler that spans
# fewest rows, then to the one with fewest cuts, so a finer ruler has to earn its extra
# boundary by capturing something.
BLANK_FRACS = (0.98, 0.95, 0.92, 0.88, 0.84, 0.80, 0.75, 0.70, 0.60, 0.50)


def best_ruler(figures, num=None):
    """The ruler that puts the most of this page's figures inside a column."""
    num = num or T.amount
    best = None
    for bf in BLANK_FRACS:
        ruler = T.column_ruler(figures, blank_frac=bf)
        if not ruler:
            continue
        got = spanned = wordy = 0
        for f in figures:
            cs = T.cells(f, ruler)
            if cs and cs[-1] == '!':
                spanned += 1
                cs = cs[:-1]
            got += sum(1 for c in cs if num(c) is not None)
            # A finer ruler must not buy figures by chopping words up. FY2019's grand
            # total came through as `GRAND` and `TOTAL  $41,178,985.82` in two cells, so
            # the row stopped being recognised as the total and the year lost its only
            # check. Cells carrying words are counted and minimised.
            wordy += sum(1 for c in cs if re.search(r'[A-Za-z]{2}', c))
        score = (got, -spanned, -wordy, -len(ruler))
        if best is None or score > best[0]:
            best = (score, ruler)
    return best[1] if best else []


def capture(figures, ruler, cols, num=None):
    """How much of what the page prints we actually read: (captured, printed)."""
    num = num or T.amount
    printed = sum(len(T.MONEY_TOKEN.findall(f)) for f in figures)
    got = 0
    for f in figures:
        cs = [c for c in T.cells(f, ruler) if c != '!']
        got += sum(1 for i in cols if i < len(cs) and num(cs[i]) is not None)
    return got, printed


# What the columns MEAN, where the table states an identity that can establish it.
#
# `v1` is an ordinal: the first column of this page that held figures. It is not a column
# of the report. FY2011 page 62 puts TOTAL AVAILABLE in v1, page 64 puts APPROPRIATED
# there and page 61 has only three of the six columns at all -- and the run's reconciliation
# was summing all of them together and calling the answer `appropriated`. The year came out
# within 1% of its own printed total by cancellation, which is the worst possible outcome:
# a wrong number that looks checked.
#
# The header cannot settle it -- only 46 of the 122 appropriations pages print four or more
# of the six headings in a rendering we can read. The table's own arithmetic can:
#
#     TOTAL AVAILABLE = APPROPRIATED + TOTAL FUNDS FORWARD
#     BALANCE TO REVENUE = TOTAL AVAILABLE - TOTAL EXPENDED - ENCUMBERED
#
# The columns are printed in a fixed order, so the only question is which of the six each
# found column is -- at most twenty possibilities, scored against every row on the page.
# A page where the winner does not beat its rivals is recorded as `not established` rather
# than guessed, and its run reconciles positionally with that said in as many words.
LINE_NO = re.compile(r'^(\d{1,3}[A-Za-z]?)[.]?$')
# Money in the omnibus budget always prints its cents or its thousands separator, and a
# bare `37` is the report's own line numbering. Read as a figure it appropriated the line
# number of the next panel to the line before it:
#     `3B. Bond Issuance Costs  $     37  Planning Board  102,729.00`
# gave Bond Issuance Costs a budget of thirty-seven dollars.
#
# The test is on the SEPARATOR, not the shape of the whole token, because OCR puts noise on
# the front of these: FY2011 prints the school department as `$ .14,908,820.00`, and a
# pattern anchored at the start of the token rejected $14.9M of a $26.6M budget.
def looks_like_amount(tok):
    t = tok.strip().strip('_.,;:').replace(' ', '')
    # `S` for `$`, which OCR confuses constantly. FY2019 prints its schools total as
    # `Total Schools  _S 21,597,536.23` and the token was read as words.
    t = re.sub(r'^[Ss_]+(?=[\d(])', '$', t)
    if not t or not re.fullmatch(r'\(?\$?-?[\d.,]+\)?', t):
        return False
    core = t.strip('()').lstrip('$').lstrip('-')
    return bool(core) and (',' in core or re.search(r'\.\d{2}$', core))


def read_omnibus_line(line):
    """`3A  Administrative Fees-Loans  $  7,196.00` -> [('3A', 'Administrative
    Fees-Loans', [7196.00])].

    The omnibus budget does not need a column ruler and is damaged by one. It prints a line
    number, a purpose and the sum voted, and the sum runs to the end of the field -- so the
    figures ARE the columns, exactly as they are for the election tallies. Read through the
    ruler instead, FY2016 page 174 produced `Principal-Loans` with a value of 1.00, which
    is its line number, and no appropriation at all.

    **Returns a LIST, because these pages print two panels side by side.** FY2015 page 140
    prints

        23  Town Accountant  169,137.00        Total Protection  $  2,638,990.00

    -- two independent votes on one printed line. Taking the trailing figure paired
    `Town Accountant` with the police, fire and building total, and every figure was real
    while every pairing was false. The line is walked instead: text accumulates into a
    label until a figure appears, the pair is emitted, and the walk continues.
    """
    out, label, lineno, dollar = [], [], '', False
    for tok in re.split(r'\s{2,}|\t', line.strip()):
        tok = tok.strip()
        if not tok:
            continue
        if tok == '$':
            # A lone `$` is the head of a figure. If TEXT follows it instead, the figure it
            # belonged to did not survive and what follows is the next panel:
            #   `Unemploy. Expense-Stab Fund  $   Subtotal Police  $  1,415,599.00`
            # Read straight through, that made one row named for both and gave the police
            # subtotal to the stabilisation fund.
            dollar = True
            continue
        if dollar and not looks_like_amount(tok):
            if label and re.search(r'[A-Za-z]{2}', ' '.join(label)):
                out.append((lineno, ' '.join(label).strip(), []))
            label, lineno, dollar = [], '', False
        # A total begins a new panel wherever it appears but at the start.
        #
        # `Capital - Facilities & Grounds   Total Schools   16,831,683.00` is two rows: a
        # capital line whose figure did not survive, and the schools total. Joined, the
        # schools total was appropriated under the name of the capital line.
        if label and is_total(tok):
            out.append((lineno, ' '.join(label).strip(), []))
            label, lineno = [], ''
        if LINE_NO.match(tok):
            # A line number begins a row. If one arrives while a label is open, that
            # label's own figure did not survive and the next panel has started.
            if label and re.search(r'[A-Za-z]{2}', ' '.join(label)):
                out.append((lineno, ' '.join(label).strip(), []))
            label, dollar = [], False
            lineno = LINE_NO.match(tok).group(1)
            continue
        if looks_like_amount(tok):
            dollar = False
            v = T.amount(re.sub(r'^[_Ss]+(?=[\d(])', '$', tok.strip().strip('_;:')))
            text = ' '.join(label).strip()
            if v is not None and (re.search(r'[A-Za-z]{2}', text) or lineno):
                # A figure under a line number whose label sits on another printed line is
                # kept with an empty label rather than dropped. `42  48,200.00` is the
                # police lock-up, whose name is on the line above; dropping the row would
                # remove $48,200.00 from the town's budget and shift nothing.
                out.append((lineno, text, [v]))
                label, lineno = [], ''
                continue
            # A figure with no label yet is part of the label's own text -- a year, an
            # article number -- or a second column of the same row. Keep it with the label
            # rather than inventing a row for it.
            label.append(tok)
            continue
        label.append(tok)
    text = ' '.join(label).strip()
    if text and re.search(r'[A-Za-z]{2}', text):
        out.append((lineno, text, []))
    return out


def trailing_amounts(line):
    """The first reading of a line, for deciding what family the page is."""
    got = read_omnibus_line(line)
    return got[0] if got else None


NAMED_COLUMNS = {
    ('appropriations', 'accountant-schedule'): ('appropriated', 'forward', 'available',
                                                'expended', 'encumbered', 'balance'),
}

# One dataset, two tables. They are not the same table and must not share a column model.
#
# `appropriations` was catalogued by subject, and the subject appears twice in every report:
# the Town Accountant's schedule of the year that CLOSED (six columns, appropriated through
# balance to revenue) and the town meeting's omnibus budget for the year AHEAD (a line
# number, a purpose, and one amount that was voted). Asking the accountant's six-column
# identity of an omnibus page is asking a question the page does not answer, and 43 of the
# 51 pages reported as `columns not established` are that -- correctly, but for a reason
# the reader could not see.
#
# So the family is detected from the page and written on every row as `table_family`. It is
# a DISCRIMINATOR: a column whose value says which variant a row is, so that a query cannot
# quietly average an appropriation voted for next year against one spent last year.
FAMILY_MARKS = (
    ('omnibus-budget', re.compile(
        r'OMNIBUSBUDGET|LINENO|LINE#|ANNUALTOWNMEETING|SPECIALTOWNMEETING')),
    ('accountant-schedule', re.compile(
        r'SUMMARY&?CLASSIFICATION|GENERALFUNDAPPROPRIATION|PROGRAMNAME')),
)


def family_of(dataset, lines):
    """Which of a dataset's table families this page is, from what the page prints.

    By its heading where it prints one, and otherwise by its SHAPE. FY2012 pages 81-83 and
    FY2019 pages 161-164 print no heading either instrument can read, and taken for the
    accountant's schedule they contributed their own line numbers to the town's budget:
    `Lunenburg Public Library  82`.

    The shape that tells them apart is the line numbering. The omnibus budget numbers every
    account it votes -- `1 Principal-Loans`, `3A Administrative Fees-Loans`, `43 Fire
    Department` -- and the accountant's schedule numbers nothing.
    """
    if dataset != 'appropriations':
        return ''
    top = squash(' '.join(lines[:9]))
    for name, mark in FAMILY_MARKS:
        if mark.search(top):
            return name
    read = [trailing_amounts(l) for l in lines]
    read = [r for r in read if r]
    if read and sum(1 for n, _, _ in read if n) >= 0.25 * len(read):
        return 'omnibus-budget'
    return ''


def name_columns(rowvals, names, ncols):
    """Which printed column each found column is, from the table's own identities.

    `rowvals` is a list of per-row value lists, one entry per found column. Returns
    (assignment, net, ok, bad) -- assignment maps found-column index to a name, or None
    when nothing scored positively.

    A found column may be left UNNAMED. The ruler sometimes finds a column the report does
    not have: a stray split, a fragment of a label, the `fwd` marker in a column of its
    own. Forcing every found column to be one of the six made a page with one spurious
    column score worse than chance and lose its names entirely -- and it is the page's
    columns, not ours, that the identity is about.
    """
    best = None
    k = len(rowvals[0]) if rowvals else 0
    if not k:
        return (None, 0, 0, 0)
    for m in range(min(k, len(names)), 1, -1):
        for which in itertools.combinations(range(k), m):
            for assign in itertools.combinations(names, m):
                idx = dict(zip(assign, which))
                ok = bad = 0
                for vs in rowvals:
                    def g(n):
                        return vs[idx[n]] if n in idx else None
                    a, f, av, ex, en, b = (g(n) for n in names)
                    if a is not None and av is not None:
                        if abs(a + (f or 0.0) - av) <= 0.02:
                            ok += 1
                        else:
                            bad += 1
                    if av is not None and ex is not None and b is not None:
                        if abs(av - ex - (en or 0.0) - b) <= 0.02:
                            ok += 1
                        else:
                            bad += 1
                score = (ok - bad, m)
                if best is None or score > best[0]:
                    best = (score, idx, ok, bad)
    if not best or best[0][0] <= 0:
        return (None, 0, 0, 0)
    (net, _), idx, ok, bad = best
    return (idx, net, ok, bad)


# Two of the fifteen families in the plan already have a dedicated extractor that ties.
#
# The generic one produces a second, worse copy of the same table -- 12 of 14 receipts
# editions failing their check against 504 rows that tie twice over, and 14 of 16 special
# revenue editions failing against 693 that prove themselves on the fund identity. Two
# files for one thing is the ambiguity this archive exists to remove: a reader cannot tell
# which is the figure, and a query that picks the wrong one is not wrong in any visible way.
SUPERSEDED = {
    'receipts': ('sources/data/annual-report-receipts.csv',
                 'scripts/extract_annual_receipts.py'),
    'special_revenue': ('sources/data/special-revenue-funds.csv',
                        'scripts/extract_special_revenue.py'),
}


def extract(dataset):
    counts = dataset in COUNT_DATASETS
    num = T.count if counts else T.amount
    rows, ledger = [], []
    for edition, pages_wanted in sorted(plan_for(dataset).items()):
        # Two renderings, chosen PER PAGE.
        #
        # OCR geometry usually preserves column position where the text layer collapses it,
        # so it is tried first. But not always: on the election tally pages the OCR
        # rendering rules into no columns at all while the text layer rules cleanly, and
        # taking OCR for the whole document dropped every election, enrolment and vital
        # records table to zero rows.
        #
        # There is no right rendering of a page, only a right one for the question being
        # asked of it — so the choice is made where the question is, one page at a time.
        ocr_pages = RP.load(edition, ocr=True)
        txt_pages = RP.load(edition)
        pages = {}
        for p_ in set(ocr_pages) | set(txt_pages):
            a, b = ocr_pages.get(p_, []), txt_pages.get(p_, [])
            ra = len(T.column_ruler(T.figure_rows(a, counts))) if a else 0
            rb = len(T.column_ruler(T.figure_rows(b, counts))) if b else 0
            pages[p_] = a if ra >= max(2, rb) else (b if rb >= 2 else (a or b))
        got = [p for p in pages_wanted if p in pages]
        if not got:
            continue
        fy = int(re.search(r'(\d{4})', edition).group(1))
        group, header, grand = '', '', []
        n0 = len(rows)

        # A table is a contiguous run of pages, and the FAMILY is a property of the table,
        # not of the page. Only 46 of the 122 appropriations pages print a heading we can
        # read -- FY2011's schedule prints none at all -- so a page-by-page reading left
        # two thirds of the accountant's schedule unrecognised and unnamed. The run votes,
        # and every page in it is the family the run is.
        runs, cur = [], []
        for pg_ in got:
            if cur and pg_ != cur[-1] + 1:
                runs.append(cur)
                cur = []
            cur.append(pg_)
        if cur:
            runs.append(cur)
        page_family = {}
        for run in runs:
            votes = collections.Counter()
            for pg_ in run:
                f = family_of(dataset, [l for l in pages[pg_] if l.strip()])
                if f:
                    votes[f] += 1
            fam = votes.most_common(1)[0][0] if votes else (
                'accountant-schedule' if dataset == 'appropriations' else '')
            for pg_ in run:
                page_family[pg_] = fam

        for page in got:
            lines = [l for l in pages[page] if l.strip()]
            if len(lines) < 4:
                continue
            family = page_family.get(page, '')
            page_first = len(rows)
            # For a tally table, try reading the trailing figures off the TEXT layer
            # first -- it keeps the digits the geometry lost.
            if counts:
                # Try the trailing-figure reading on BOTH renderings and keep the fuller.
                #
                # Neither is reliably better. The FY2016 election page needs the text
                # layer, whose OCR never recognised the standalone zeros. The FY2025 page
                # needs the OCR, because its text layer holds different content entirely --
                # and reading only the text layer there dropped two of five columns from
                # every row, so `135 90 84 155 464` came through as `135 90 464` and the
                # ballot identity failed on all sixteen rows.
                cand = [trailing_numbers(
                            [l for l in txt_pages.get(page, []) if l.strip()], num),
                        trailing_numbers(lines, num)]
                alt = max(cand, key=lambda c: (sum(len(v) for _, v in c), len(c)))
                if alt and sum(len(v) for _, v in alt) > 0:
                    for label, vals in alt:
                        kind = ('grand_total' if is_grand(label)
                                else 'subtotal' if is_total(label) else 'row')
                        if GROUP.match(label) and not vals:
                            group = label.strip()
                            continue
                        rows.append({
                            'dataset': dataset, 'fy': fy, 'edition': edition,
                            'page': page, 'panel': 1, 'group': group,
                            'label': label, 'label_missing': '', 'kind': kind,
                            'table_family': family,
                            'columns_as_printed': header or 'trailing figures',
                            **{f'v{i + 1}': ('' if v is None else str(v))
                               for i, v in enumerate(vals[:8])},
                            'n_values': sum(1 for v in vals if v is not None),
                            'ruler_spanned': '', 'repaired_cells': 0,
                            'unparsed_cells': '',
                        })
                    continue

            # The omnibus budget is read by its trailing amount, from whichever
            # rendering holds more of its lines. It has one money column and no identity,
            # so nothing is bought by a ruler and a great deal is lost to one: the OCR of
            # these pages drops whole lines that the text layer keeps -- 21 of the 22 on
            # FY2016 page 174 -- and the ruler cannot see that because it only ever looks
            # at the rendering it was given.
            if family == 'omnibus-budget':
                best_lines, best_read = None, []
                for cand in (ocr_pages.get(page, []), txt_pages.get(page, [])):
                    read = [g for l in cand if l.strip() for g in read_omnibus_line(l)]
                    if len(read) > len(best_read):
                        best_lines, best_read = cand, read
                if best_read:
                    if not header:
                        header = ' | '.join(
                            re.sub(r'\s{2,}', ' ', l.strip())
                            for l in (best_lines or [])[:6]
                            if not T.MONEY_TOKEN.search(l))[:200]
                    for lineno, label, vals in best_read:
                        if is_column_heading(label):
                            continue
                        line_sq = squash(label)
                        kind = ('grand_total' if is_grand(label) or 'GRANDTOTAL' in line_sq
                                else 'subtotal' if is_total(label)
                                or line_sq.startswith('TOTAL') else 'row')
                        if GROUP.match(label) and not vals:
                            group = label.strip()
                            continue
                        rows.append({
                            'dataset': dataset, 'fy': fy, 'edition': edition,
                            'page': page, 'panel': 1, 'group': group,
                            'label': label, 'label_missing': '', 'kind': kind,
                            'table_family': family, 'line_no': lineno,
                            'columns_as_printed': header or 'trailing amounts',
                            **{f'v{i + 1}': f'{v:.2f}'
                               for i, v in enumerate(vals[:8])},
                            'n_values': len(vals),
                            'ruler_spanned': '', 'repaired_cells': 0,
                            'unparsed_cells': '',
                        })
                    name_this_page(rows[page_first:], dataset, family,
                                   max(len(v) for _, _, v in best_read))
                    continue

            # The searched ruler is used ONLY where the columns can afterwards be named.
            #
            # It buys capture and it spends column identity, and the two are the same
            # transaction. A finer cut recovers figures a coarse one merged away -- FY2011
            # page 64 went from 43 of its 98 figures to 93 -- but it also changes WHICH
            # column comes first, and everything downstream calls that one `v1`. On the
            # capital projects schedule that turned a year reconciling to $2,144.75 into
            # one whose v1 summed to $79.00, because v1 had become a column of item
            # numbers. On a tally table the objective rewards the wrong thing outright: a
            # page of names and years yields more integers the finer it is cut, and the
            # officials list went from 237 rows to 818 by slicing names in half --
            # `Deborah Seeley   20`, `2011 Richard Kap`.
            #
            # So it is spent only where NAMED_COLUMNS can establish what the columns are.
            figures = T.figure_rows(lines, counts)
            ruler = (best_ruler(figures, num)
                     if (dataset, family) in NAMED_COLUMNS else T.column_ruler(figures))
            if not ruler:
                continue
            cols, n_fig = money_columns(lines, ruler, num, counts)
            if not cols:
                continue
            groups = panels(lines, ruler, num, counts)
            if len(groups) < 2:
                groups = [(None, cols)]
            if not header:
                header = ' | '.join(
                    re.sub(r'\s{2,}', ' ', l.strip())
                    for l in lines[:8] if not T.MONEY_TOKEN.search(l))[:200]
            for line in lines:
                cells0 = T.cells(line, ruler)
                for gi, (lab_i, val_i) in enumerate(groups):
                    cells = cells0
                    # A row the ruler could not cut cleanly is FLAGGED, not discarded.
                    #
                    # Skipping them threw away real data: `Teacher Quality #140` on FY2020
                    # page 32 had the closing bracket of `($0.24)` fall across a gutter, so the
                    # row was marked spanned and dropped -- with all four of its values parsed
                    # correctly. The dataset's own reconciliation then came up short by exactly
                    # that row's disbursements figure, $31,793.00.
                    #
                    # A dropped row shifts nothing and is invisible. A flagged row can be
                    # looked at.
                    spanned = '!' in cells
                    cells = [c for c in cells if c != '!']
                    # In a multi-panel page the label is the panel's OWN label column,
                    # not the first text found on the line -- which on a two-panel wage
                    # list is always the left-hand person, whatever panel we are reading.
                    if lab_i is None:
                        label = next((c for c in cells if is_label(c)), '')
                    else:
                        idx = lab_i if isinstance(lab_i, list) else [lab_i]
                        label = ' '.join(cells[i].strip() for i in idx
                                         if i < len(cells) and cells[i].strip())
                    # A row whose label did not survive OCR is KEPT, with the label
                    # empty and flagged. Dropping it loses figures that parsed perfectly:
                    # `Flat Hill Culvert Design - DPW  $112,500.00 | $112,500.00 | $0.00`
                    # came through with all three values and no name, and vanished.
                    #
                    # An empty label is visible. A missing row is not.
                    if not label or not is_label(label):
                        label, no_label = '', True
                    else:
                        no_label = False
                    vals = [num(cells[i]) if i < len(cells) else None
                            for i in val_i]
                    if not counts:
                        vals, dollar_fix = repair_dollar_as_five(vals, cells, val_i)
                    else:
                        dollar_fix = 0
                    # A cell that plainly holds a figure and did not parse is recorded, not
                    # dropped. A dropped cell shifts nothing and so is invisible downstream --
                    # which is how `$29.075.55` vanished from a row whose other three columns
                    # were correct, and why nothing arithmetic could notice.
                    repaired = dollar_fix + sum(
                        1 for i in val_i
                        if i < len(cells) and T.was_repaired(cells[i]))
                    unparsed = [cells[i] for i in val_i
                                if i < len(cells) and num(cells[i]) is None
                                and T.looks_like_money(cells[i])]
                    if not any(v is not None for v in vals):
                        if GROUP.match(label):
                            group = label.strip()
                        continue
                    # What KIND of row this is comes off the PAGE, not off our cut of it.
                    #
                    # The ruler decides where the label ends, and a ruler that cuts a
                    # little finer split FY2019's `GRAND TOTAL` into `GRAND` and
                    # `TOTAL  $41,178,985.82` -- so the row stopped being the grand total
                    # and the year silently lost the only check it had. The page still
                    # said GRAND TOTAL. Read it there.
                    line_sq = squash(line)
                    kind = ('grand_total' if is_grand(label) or 'GRANDTOTAL' in line_sq
                            else 'subtotal' if is_total(label) or line_sq.startswith('TOTAL')
                            else 'row')
                    if kind == 'grand_total':
                        grand = vals
                    rows.append({
                        'dataset': dataset, 'fy': fy, 'edition': edition, 'page': page,
                        'group': group, 'label': label.strip(), 'kind': kind,
                        'columns_as_printed': header,
                        **{f'v{i + 1}': ('' if v is None else
                                     (str(v) if counts else f'{v:.2f}'))
                           for i, v in enumerate(vals[:8])},
                        'n_values': sum(1 for v in vals if v is not None),
                        'table_family': family,
                        'ruler_spanned': 'yes' if spanned else '',
                        'repaired_cells': repaired,
                        'unparsed_cells': ' | '.join(unparsed),
                    })
            name_this_page(rows[page_first:], dataset, family, len(groups[0][1]))
        # Reconcile per TABLE, not per edition.
        #
        # An edition often prints the same subject twice in different forms — FY2020 has
        # the accountant's appropriations schedule on pages 26-30 and the town meeting
        # omnibus budget on 151-155, each with its own grand total. Summing the two gave
        # $161,209,998.22 against a printed $43,104,912.84, which says nothing about
        # either. A table is a contiguous run of pages; each run is checked against its own
        # total.
        for run in runs:
            in_run = [r for r in rows[n0:] if r['page'] in run]
            mark_page_furniture(in_run)
            mark_arithmetic_subtotals(in_run)
            mine = [r for r in in_run if r['kind'] == 'row']
            if not in_run:
                continue
            grand_row = next((r for r in in_run if r['kind'] == 'grand_total'), None)
            grand = ([float(grand_row[f'v{i}']) for i in range(1, 9)
                      if grand_row.get(f'v{i}') not in (None, '')]
                     if grand_row else [])
            checks, ties = [], []
            fam = next((r.get('table_family') for r in in_run if r.get('table_family')), '')
            names = (NAMED_COLUMNS.get((dataset, fam))
                     or (('recommended', 'voted') if fam == 'omnibus-budget' else None))
            named_run = bool(names) and all(r.get('_names') for r in in_run)
            if named_run and grand_row:
                # Reconcile BY NAME. `v1` is where a figure landed on one page, not a
                # column of the report -- see NAMED_COLUMNS. Summing v1 across a run added
                # one page's APPROPRIATED to another page's TOTAL AVAILABLE and compared
                # the result to a printed appropriation.
                def cell(r, name):
                    c = (r.get('_names') or {}).get(name)
                    v = r.get(f'v{c}') if c else None
                    try:
                        return float(v) if v not in (None, '') else None
                    except ValueError:
                        return None

                for name in names:
                    printed = cell(grand_row, name)
                    if printed is None:
                        continue
                    got_sum = round(sum(cell(r, name) or 0.0 for r in mine), 2)
                    ok = abs(got_sum - printed) <= 0.02
                    ties.append(ok)
                    checks.append(f'{name}: {got_sum:,.2f} vs {printed:,.2f}'
                                  + ('' if ok else f' ({got_sum - printed:+,.2f})'))
            else:
                # An ordinal must say it is one, EVERY time it is quoted.
                #
                # The caveat used to be appended to the first column of a run only, so a
                # run reporting four columns disclaimed one of them and presented the other
                # three as though they were columns of the report.
                if names:
                    unnamed = (' [v-numbers are ORDINALS, not columns: not established on '
                               f'{sum(1 for r in in_run if not r.get("_names"))} of '
                               f'{len(in_run)} rows]')
                else:
                    unnamed = (' [v-numbers are ORDINALS, not columns: this table family '
                               'has no column model, so the same v-number is a different '
                               'printed column on different pages]')
                # Take the grand total's columns BY POSITION, not compacted.
                #
                # Compacting its non-empty cells into a list and pairing them with v1, v2,
                # v3... shifts every column after the first blank one: a grand total row
                # holding v1, v2, v3 and v5 had our v4 sum compared against the report's
                # v5. That is the shift this whole extractor exists to prevent, in the
                # check itself.
                for i in range(1, 9):
                    printed = grand_row.get(f'v{i}') if grand_row else None
                    if printed in (None, ''):
                        continue
                    printed = float(printed)
                    col = f'v{i}'
                    got_sum = round(sum(float(r[col]) for r in mine if r.get(col)), 2)
                    ok = abs(got_sum - printed) <= 0.02
                    ties.append(ok)
                    checks.append(f'{col}: {got_sum:,.2f} vs {printed:,.2f}'
                                  + ('' if ok else f' ({got_sum - printed:+,.2f})')
                                  + unnamed)

            if dataset == 'elections':
                # Only FULL rows can be checked; a row missing cells tests our extraction
                # against itself. The table's width is the commonest row width on the page,
                # since a report mixes a five-column town election with a seven-column
                # state primary.
                widths = collections.Counter()
                for r in in_run:
                    w = sum(1 for i in range(1, 9) if r.get(f'v{i}') not in (None, ''))
                    if w >= 3:
                        widths[(r['page'], w)] += 1
                full = {}
                for (pg_, w), n_ in widths.items():
                    if n_ > widths.get((pg_, full.get(pg_, 0)), 0):
                        full[pg_] = w
                ok_rows = bad_rows = short = 0
                for r in in_run:
                    vs = [r.get(f'v{i}') for i in range(1, 9)]
                    vs = [v for v in vs if v not in (None, '')]
                    width = full.get(r['page'])
                    if len(vs) < 3 or len(vs) != width:
                        # A row one cell short can still be recovered from its own total.
                        #
                        # Vision misses individual figures on these scans: FY2011 p79
                        # prints `** David J. Matthews 20 21 33 30 104` and never
                        # recognised the 33, at scale 6 or at scale 9. The row constrains
                        # it exactly — 104 − (20+21+30) = 33.
                        #
                        # It is written to `derived_cell`, never into a value column, and
                        # the column it belongs to is NOT asserted: the reading is
                        # positionless, so we know a cell is missing and what it must be,
                        # but not where it sat. Rule 7 — an inference is not promoted to a
                        # reading because it happens to be certain.
                        if width and len(vs) == width - 1 and len(vs) >= 3:
                            parts = [int(float(v)) for v in vs[:-1]]
                            total = int(float(vs[-1]))
                            gap = total - sum(parts)
                            if gap > 0:
                                r['derived_cell'] = (
                                    f'one cell missing; from this row\'s own printed '
                                    f'total it must be {gap}')
                                r['row_check'] = ('one cell short — the missing value is '
                                                  'derivable from the printed total')
                                short += 1
                                continue
                        if vs:
                            r['row_check'] = 'not a full row — not checked'
                            short += 1
                        continue
                    parts = [int(float(v)) for v in vs[:-1]]
                    total = int(float(vs[-1]))
                    if sum(parts) != total:
                        # ONE missing cell can be recovered from the row's own total.
                        #
                        # Vision misses individual figures on these scans -- FY2011 p79
                        # prints `** David J. Matthews 20 21 33 30 104` and never
                        # recognised the 33, at scale 6 or 9. The row still constrains it
                        # exactly: 104 - (20+21+30) = 33.
                        #
                        # This is DERIVED, not observed, so it is written into its own
                        # column and never into the value columns, and `row_check` says so.
                        # Rule 7: an inference does not get promoted to a reading because
                        # it happens to be certain.
                        width = full.get(r['page'])
                        blanks = [i for i in range(1, width)
                                  if r.get(f'v{i}') in (None, '')] if width else []
                        if len(blanks) == 1 and total - sum(parts) > 0:
                            r['derived_cell'] = (f"v{blanks[0]} = {total - sum(parts)} "
                                                 f"(from this row's own printed total)")
                    if sum(parts) == total:
                        r['row_check'] = 'parts sum to the printed total'
                        ok_rows += 1
                    else:
                        r['row_check'] = (f'parts sum to {sum(parts)}, '
                                          f'total printed {total}')
                        bad_rows += 1
                if ok_rows and not bad_rows:
                    checks.append(f'{ok_rows} full rows: parts sum to their printed total'
                                  + (f'; {short} partial not checked' if short else ''))
                    ties.append(True)
                elif ok_rows or bad_rows:
                    checks.append(f'{ok_rows} full rows tie, {bad_rows} do not'
                                  + (f'; {short} partial not checked' if short else ''))
                    ties.append(False)

            if fam == 'omnibus-budget':
                # The table numbers its own lines, so it proves its own completeness.
                #
                # A gap in the numbering is a row that is not here. FY2021's omnibus runs
                # 78, 79B, 80 -- line 79 is the school department, $21.6M of a $39.9M
                # budget, and it is absent from both renderings of both pages it could be
                # on. Nothing else in the extraction could have told us that: a missing row
                # shifts nothing, and the residual alone cannot say whether one large row
                # is gone or fifty small ones are wrong.
                seen = set()
                for r in in_run:
                    m = re.match(r'^(\d{1,3})', r.get('line_no') or '')
                    if m:
                        seen.add(int(m.group(1)))
                if seen:
                    gaps = [n for n in range(min(seen), max(seen) + 1) if n not in seen]
                    if gaps:
                        checks.append(
                            f'line numbering {min(seen)}-{max(seen)}: '
                            f'{len(gaps)} numbers we did not read — a missing row, a row '
                            f'read without its number, or one the report does not use ('
                            + ', '.join(str(g) for g in gaps[:12])
                            + ('…' if len(gaps) > 12 else '') + ')')
                        ties.append(False)
                    else:
                        checks.append(f'line numbering {min(seen)}-{max(seen)}: complete')
                        ties.append(True)

            # THREE states, not two.
            #
            # `partial` was doing the work of two different facts and implying a third that
            # was never true. These reports are the official record — Town Manager and
            # Finance Committee approved, carrying MUNIS exports — so the town's figures
            # are not in question. A table printing no total is not less authoritative; it
            # simply cannot be checked by arithmetic, and calling that `partial` said the
            # data was doubtful when what was doubtful was our reading of it.
            if not ties:
                status = 'no check'
            elif all(ties):
                status = 'checked'
            else:
                status = 'check failed'
            for r in in_run:
                r['status'] = status
                r['reconciliation'] = ' ; '.join(checks) or 'no total printed'
            ledger.append({'edition': edition + (f' p{run[0]}-{run[-1]}'
                                                 if len(runs) > 1 else ''),
                           'pages': len(run), 'rows': len(mine),
                           'status': status, 'checks': checks})
    return rows, ledger


def repair_dollar_as_five(vals, cells, idx):
    """`$` read as `5`, caught by comparing a row against itself.

    Vision reads the dollar sign as a `5` on some scans, and the result is a perfectly
    valid number ten times too large — `$1,770,967.83` becomes `51,770,967.83`. Nothing in
    the cell says it is wrong, and one such row put FY2020's appropriations $73.5M over its
    own printed total.

    What gives it away is the row: these schedules print the same figure in more than one
    column, so the correct reading is usually sitting beside the corrupt one.

        Transfer to Capital Project Fund   51.770,967.83   $1,770,967.83   51,770,967.8
        GRAND TOTAL                        S43,104,912.84  543,104,912.84  541,024,362.4

    So a value is repaired only when dropping its leading `5` makes it match another value
    in the same row. That is evidence from the document rather than a guess about the
    digit, and a row with no corroborating column is left alone.
    """
    out, repaired = list(vals), 0
    for i, v in enumerate(out):
        # No magnitude gate. An earlier version only looked at values over $1M and so
        # missed `$7,535.55` read as `57535.55` sitting beside two correct readings of the
        # same figure. The evidence is the sibling match, not the size.
        if v is None or v <= 0:
            continue
        raw = str(int(v)) if float(v).is_integer() else f'{v:.2f}'
        if not raw.startswith('5'):
            continue
        try:
            alt = float(f'{v:.2f}'.lstrip('5')) if f'{v:.2f}'.startswith('5') else None
        except ValueError:
            alt = None
        if alt is None:
            continue
        for j, w in enumerate(out):
            if j != i and w is not None and abs(w - alt) < 0.02:
                out[i] = alt
                repaired += 1
                break
    return out, repaired


FOOTNOTE = re.compile(r'FORWARDFROMFY|CARRIEDFORWARDFROM|SEENOTE')


def name_this_page(page_rows, dataset, family, ncols):
    """Stamp each row of one page with what its value columns MEAN, or say we do not know.

    Written into `column_meaning` so a reader of the CSV can see it, and into `_names` for
    the reconciliation, which sums the column named `appropriated` rather than whichever
    column happened to come first on that page.
    """
    if family == 'omnibus-budget':
        name_omnibus_page(page_rows, ncols)
        return
    names = NAMED_COLUMNS.get((dataset, family))
    if not names or not page_rows or not ncols:
        return
    rowvals = []
    for r in page_rows:
        vs = []
        for c in range(1, ncols + 1):
            v = r.get(f'v{c}')
            try:
                vs.append(float(v) if v not in (None, '') else None)
            except ValueError:
                vs.append(None)
        if sum(1 for v in vs if v is not None) >= 2:
            rowvals.append(vs)
    assign, net, ok, bad = name_columns(rowvals, names, ncols)
    if not assign:
        for r in page_rows:
            r['column_meaning'] = ('not established -- this page states no identity that '
                                   'fixes which printed column is which')
        return
    lookup = {n: i + 1 for n, i in assign.items()}
    meaning = ' | '.join(f'v{c}={n}' for n, c in sorted(lookup.items(), key=lambda t: t[1]))
    for r in page_rows:
        r['column_meaning'] = f'{meaning} (identity holds {ok}, fails {bad})'
        r['_names'] = lookup


def name_omnibus_page(page_rows, ncols):
    """The omnibus budget has no identity to test. It has a SHAPE.

    `LINE #  |  ACCOUNT  |  amount` -- a line number, a purpose, and the sum voted. There is
    no second column to check the first against, so the columns are named from what they
    hold: a column of small whole numbers with no cents is the report's own line numbering,
    and the money column is what town meeting voted.

    This matters because the line numbers were being appropriated. FY2011 page 84 prints
    `11  Historical Commission  $850.00`, and with the ruler cutting before the `11` that
    row contributed eleven dollars to the town's budget in the first column and $850.00 in
    the second, so neither column was the appropriation.
    """
    if not page_rows or not ncols:
        return
    kind = {}
    for c in range(1, ncols + 1):
        vals = []
        for r in page_rows:
            v = r.get(f'v{c}')
            if v in (None, ''):
                continue
            try:
                vals.append(float(v))
            except ValueError:
                pass
        if not vals:
            continue
        # A line number: a whole number under 400, no cents, in nearly every row that has
        # one. Money in these schedules runs to hundreds and to cents.
        if sum(1 for v in vals if v == int(v) and 0 < v < 400) >= 0.9 * len(vals):
            kind[c] = 'line_no'
        else:
            kind[c] = 'voted'
    money = [c for c, k in kind.items() if k == 'voted']
    lookup = {}
    if len(money) == 1:
        lookup = {'voted': money[0]}
    elif len(money) > 1:
        # Two money columns is the year printing what was recommended and what was voted.
        # The last is what passed; it is the one the town raised.
        lookup = {'recommended': money[0], 'voted': money[-1]}
    meaning = ' | '.join(f'v{c}={k}' for c, k in sorted(kind.items()))
    for r in page_rows:
        r['column_meaning'] = (meaning + ' (from the shape of the column, not an identity)'
                               if meaning else
                               'not established -- no column on this page held figures')
        if lookup:
            r['_names'] = lookup


def mark_page_furniture(rows_in):
    """Take the page's furniture back out of the table.

    Two things that are printed on the page are not lines of the schedule, and both were
    being summed as though they were appropriations.

    **The footer legend.** The accountant's schedule explains its own `fwd` marker at the
    foot of the last page, and gives the total carried forward beside it:

        fwd - forward from FY 2015                                        $265,386.55

    That is a key to a symbol, not a program. Counted as detail it added between
    $207,450.46 and $838,486.09 to a year -- 55% of FY2011's entire residual.

    **The page number.** A bare figure alone on a line, equal to the number printed at the
    foot of the page, is the page number. Thirty-two of them were being appropriated.

    Both are marked rather than dropped, because a marked row can be looked at and a
    dropped one cannot. Anything printed AFTER the run's grand total is footer by
    position: the grand total ends the table.
    """
    seen_grand = False
    for r in rows_in:
        if r['kind'] == 'grand_total':
            seen_grand = True
            continue
        vals = [r.get(f'v{i}') for i in range(1, 9)]
        vals = [v for v in vals if v not in (None, '')]
        if (not r['label'].strip() and len(vals) == 1
                and abs(float(vals[0]) - int(r['page'])) < 0.001):
            r['kind'] = 'page_number'
            r['row_check'] = 'the page number, not a line of the table'
        elif FOOTNOTE.search(squash(r['label'])):
            r['kind'] = 'footnote'
            r['row_check'] = "the schedule's own key to its `fwd` marker, not a program"
        elif seen_grand and r['kind'] == 'row':
            r['kind'] = 'footnote'
            r['row_check'] = 'printed below the grand total, which ends the table'


def mark_arithmetic_subtotals(rows_in, tol=0.02):
    """Find subtotal rows by ARITHMETIC, not by their label.

    These schedules print a department's lines and then its total, and the total's label
    frequently does not survive extraction -- it comes through blank, or as the department
    name alone. Counted as detail it is added to the very lines it summarises, so the table
    sums to far more than its own printed grand total: FY2011's appropriations came to
    $46,269,199.78 against a printed $27,948,061.40, with exactly one subtotal recognised
    among 173 rows.

    The reliable test is what the number IS. A row whose value equals the sum of the
    consecutive rows immediately above it is their total, whatever it is called:

        Payroll             10,241,099.90
        Other Expenses       4,111,404.61
        (no label)          14,352,504.51   <- the sum of the two above

    **Tested in EVERY column, not the first.** The schedule prints the same identity across
    all six of its columns, and OCR does not damage them all at once. FY2022 page 31 prints
    the school department total as

        Payroll          15,590,214.00  15,590,214.00 ...
        Other Expenses                   6,061,478.05 ...
        (no label)       21,651,692.05  21,651,692.05 ...

    -- the appropriated figure for Other Expenses is missing, so the identity fails in the
    first column and holds exactly in the second. Testing only the first left a
    $21,651,692.05 subtotal classed as detail and put the year $28.7M over its own printed
    total. Four rows on that one page failed the same way, two of them because OCR had put
    an extra digit on the front of the total itself.

    **A row that HAS a label must tie in two columns.** Two real line items can sum to a
    third by coincidence, and a coincidence that survives in two independent columns is a
    different order of unlikely. An unlabelled row needs only one, because a row with no
    label in these schedules is nearly always the department total whose label did not
    survive.
    """
    ncol = 8

    def col(i, c):
        v = rows_in[i].get(f'v{c}')
        try:
            return float(v) if v not in (None, '') else None
        except ValueError:
            return None

    # Two passes, because the schedules nest. A department total sums its own lines; a
    # section total then sums the department totals. Once the inner ones are marked they
    # are no longer `row`, so the outer level has to be looked for among `subtotal` rows --
    # otherwise a section total stays classed as detail and is added to everything beneath
    # it a second time.
    # Looked for in BOTH directions.
    #
    # These schedules print a department total after its lines in some sections and before
    # them in others -- FY2019's `20,190,110.47` sits above the `13,947,152.00` and
    # `6,242,958.47` that make it up. Searching only upward left that one classed as detail
    # and put the year $24M over its own printed total.
    for level, want in enumerate(('row', 'subtotal')):
        for i in range(len(rows_in)):
            if rows_in[i]['kind'] != 'row':
                continue
            labelled = bool(rows_in[i]['label'].strip())
            hits = {}
            for c in range(1, ncol + 1):
                v = col(i, c)
                if v is None:
                    continue
                for step, where in ((-1, 'above'), (1, 'below')):
                    run, n, seen = 0.0, 0, 0
                    j = i + step
                    while 0 <= j < len(rows_in) and seen < 14:
                        if rows_in[j]['kind'] != want:
                            break
                        w = col(j, c)
                        if w is None:
                            # A row with no figure in THIS column does not end the group.
                            # FY2019 prints `Payo Department` with its value lost to OCR,
                            # sitting between the two lines whose sum is the total below
                            # them -- breaking there left a $20,190,110.47 subtotal classed
                            # as detail and the year $24M over its own printed total.
                            j += step
                            seen += 1
                            continue
                        run += w
                        n += 1
                        seen += 1
                        # A single line repeated with no label of its own is that line's
                        # total: these schedules print a one-line department as the line
                        # and then the department total, identical. Counting both doubles
                        # it.
                        enough = n >= 2 or (n == 1 and not labelled)
                        if enough and abs(run - v) <= tol:
                            hits[c] = (n, where)
                            break
                        j += step
                    if c in hits:
                        break
            if not hits or (labelled and len(hits) < 2):
                continue
            c = min(hits)
            n, where = hits[c]
            rows_in[i]['kind'] = 'subtotal'
            rows_in[i]['row_check'] = (
                f'subtotal: equals the {n} '
                f'{"rows" if level == 0 else "subtotals"} {where} it, '
                f'in {len(hits)} of its columns'
                + ('' if len(hits) > 1 else f' (v{c})'))


def is_label(cell):
    """Is this cell the row's label?

    NOT `[A-Za-z]{3}` -- three consecutive letters. `PL 94-142 #240` has none, so that test
    dropped the federal special education grant out of every year of the special revenue
    schedule, silently and without shifting anything. Fund names in these tables are often
    mostly code: `Title I #305`, `PL 94-142 #240`, `FY22 Covid 19`, `25#305`.

    The real test is: it contains a letter, it is not itself a figure, and it is long
    enough not to be a stray mark.
    """
    t = (cell or '').strip()
    if len(t) < 2 or not re.search(r'[A-Za-z]', t):
        return False
    return T.amount(t) is None or bool(re.search(r'[A-Za-z]{2}', t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset', nargs='?')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()

    names = sorted({r['dataset'] for r in csv.DictReader(open(PLAN))})
    if args.list or not args.dataset:
        print('datasets in the plan:')
        for n in names:
            print('  ', n)
        return
    if args.dataset not in names:
        print(f'unknown dataset {args.dataset!r}')
        return

    if args.dataset in SUPERSEDED:
        csvf, script = SUPERSEDED[args.dataset]
        print(f'{args.dataset}: superseded. {csvf} is the figure, written by {script} '
              f'and checked against the report\'s own printed total. The generic reading '
              f'of this family is a second, worse copy of the same table and is not '
              f'written.')
        return
    rows, ledger = extract(args.dataset)
    if not rows:
        print(f'{args.dataset}: nothing extracted')
        return
    out = os.path.join(OUTDIR, f'report-{args.dataset.replace("_", "-")}.csv')
    fields = (['dataset', 'fy', 'edition', 'page', 'panel', 'group', 'label',
               'label_missing', 'kind', 'row_check', 'derived_cell',
               'table_family', 'line_no', 'columns_as_printed'] + [f'v{i}' for i in range(1, 9)]
              + ['n_values', 'ruler_spanned', 'repaired_cells', 'unparsed_cells',
                 'column_meaning', 'status', 'reconciliation'])
    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, '') for f in fields})

    # PRINT THE DENOMINATOR. An edition that produced nothing prints nothing, and nothing
    # reads as "there was nothing there" -- which is how `monty_tech` came to hold one of
    # the fifteen years the plan asks for without anybody noticing. A run that fails leaves
    # a line saying so; a run that never happens leaves silence.
    planned = set(plan_for(args.dataset))
    got_editions = {r['edition'] for r in rows}
    empty = sorted(planned - got_editions)
    if empty:
        print(f'  {len(planned) - len(empty)} of {len(planned)} planned edition(s) '
              f'produced rows. NOTHING came out of: ' + ', '.join(empty))
    else:
        print(f'  all {len(planned)} planned edition(s) produced rows')

    rec = sum(1 for l in ledger if l['status'] == 'checked')
    fail = sum(1 for l in ledger if l['status'] == 'check failed')
    none = sum(1 for l in ledger if l['status'] == 'no check')
    print(f'{args.dataset}: {len(rows)} rows, {len(ledger)} editions — '
          f'{rec} checked, {fail} check failed, {none} no check available')
    for l in ledger:
        print(f"  {l['edition']:<17}{l['pages']:>3}p {l['rows']:>5} rows  "
              f"{l['status']}"
              + (f"  [{l['checks'][0]}]" if l['checks'] else '  [no total printed]'))
    print(f'wrote {os.path.relpath(out, ROOT)}')


if __name__ == '__main__':
    main()
