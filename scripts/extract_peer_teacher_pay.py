#!/usr/bin/env python3
"""Teacher gross pay in two comparison districts, on each district's OWN salary scale.

    python3 scripts/extract_peer_teacher_pay.py            # read, select, write the aggregates
    python3 scripts/extract_peer_teacher_pay.py --check    # fail if the aggregates would change

THE QUESTION (TJ, 19 October 2026). `/school-spending-history/teachers-on-the-scale` shows that
in calendar 2025 most of Lunenburg's matched teachers were paid at least Lunenburg's master's
top step. Read alone that says "we pay most of our people too much"; but "we cannot say what
the composition of our school is compared to other schools". Lunenburg's SCALE is the lowest
of the districts with a current contract held, while DESE's AVERAGE puts it second of six. The
test this script makes possible: do another district's teachers sit as high on THEIR OWN
scale?

THE DATA. Two member towns print their school employees' gross pay by name (survey:
notes/findings/WAGE-LISTS-COMPARISON-TOWNS.md):

  Harvard   the Town of Harvard's 2025 annual report, pdf pages 228-231, "SCHOOL EMPLOYEE
            EARNINGS REPORT", which prints TEACHER as its own section with a DEPT TOTAL. THE
            PERIOD IS NOT PRINTED on those pages or anywhere else in the report that was
            searched (contents page, finance section). Both readings are carried below.
  A-W       the Town of Ashburnham's 2025 annual report, pdf pages 136-146, reprinting the
            Ashburnham-Westminster Regional School District's "Earnings In Excess of $500
            7/1/24 - 6/30/25" -- FISCAL YEAR 2025 -- with a PRIMARY JOB TITLE per person.

Both PDFs are DIGITAL (scripts/pdf_kind.py: every one of these pages is `text`), so they are
read from the text layer with positions (pdfplumber), not by OCR.

SELECTION -- WHO IS A TEACHER. Each district differently, and the difference is stated:
  * Lunenburg (extract_teacher_pay.py): names on the printed school ROSTERS under a teaching
    title, MATCHED to the town's wage list. Selection by the roster, not by the wage list.
  * Harvard: the wage list's own section headed SCHOOL / TEACHER. The town's selection,
    taken as printed; we do not know which posts it puts there.
  * A-W: OUR RULE over the printed primary job title, TEACHING_TITLES below -- grade levels,
    subjects, SPECIAL ED TEACHER, TEACHER and LIBRARIAN/MEDIA, mirroring the roster positions
    Lunenburg's page counts (classroom, specialist incl. art, music, PE and library, special
    education). Counsellors, psychologists, speech pathologists, nurses, reading specialists,
    coaches, aides, substitutes, tutors and administrators are not teachers here, and three
    titles that name a programme rather than a post (ACHIEVE, ACE, EXCEL) are left out and
    counted. A title is a PRIMARY title: pay for a second post is in the person's gross.

PART-YEAR, THE SAME RULE AS LUNENBURG'S: a selected teacher paid below half the selected
group's median is left out as part-year. OUR rule, applied identically to all three.

THE COMPARABLE MEASURE. Each full-year teacher's gross pay as a share of HIS OR HER OWN
district's master's-lane top step for the matching period:
  * a CALENDAR list: half the FY<y> cell plus half the FY<y+1> cell (Lunenburg's convention,
    OURS -- pay spread evenly over the months);
  * a FISCAL list: that fiscal year's cell.
Harvard's period is not printed, so its measure is computed both ways and the calendar
reading, the year the report is named for and the convention its neighbour Lunenburg prints,
is the one the page leads with. A-W's current schedule is NOT HELD (the only filing is
2016-2019), so its measure CANNOT BE COMPUTED: it gets counts and dollar quartiles only, and
the gap is registered.

GROSS PAY IS NOT SALARY. Stipends, coaching, summer work, extra duties, longevity and any
retroactive pay are in it. Lunenburg pays longevity outside the grid (up to $5,700 on the top
step); Harvard's agreement prints none; A-W's current agreement is not held.

PRIVACY -- RULE 13e. The towns printed every name. THIS PROJECT PUBLISHES NO PER-PERSON PAY.
The name-level rows are written to build/private/peer-teacher-pay/ (gitignored); only counts,
quartiles and bands with at least MIN_CELL people leave this script, in
sources/data/peer-teacher-pay-distribution.csv.
"""
import argparse
import collections
import csv
import io
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
PRIV = os.path.join(ROOT, 'build', 'private', 'peer-teacher-pay')
OUT = os.path.join(SRC, 'data', 'peer-teacher-pay-distribution.csv')
SCHEDULES = os.path.join(SRC, 'data', 'teacher-salary-schedules.csv')

HARVARD = ('peer-districts/harvard-annual-town-report-2025.pdf', range(228, 232))
AW = ('peer-districts/ashburnham-annual-town-report-2025.pdf', range(136, 147))
AW_HEADING = 'Earnings In Excess of $500 7/1/24 - 6/30/25'
TYNG = ('peer-districts/tyngsborough-gross-wage-report-2022.pdf', range(1, 14), range(14, 27))
TYNG_YEAR = 2022
# The master's lane, under whatever name a district's agreement prints it -- read from our table
# of the contracts, never typed. A district with no such cell for the list's period gets dollar
# quartiles only.
MA_LANES = ('Masters', 'M', 'MA')

MIN_CELL = 3
PART_YEAR = 0.5
BAND, BAND_LO, BAND_HI = 10000, 40000, 120000
PCT_BAND, PCT_LO, PCT_HI = 10, 60, 130
FIELDS = ['district', 'period', 'measure', 'value', 'unit', 'note']


def fail(msg):
    print('extract_peer_teacher_pay: %s' % msg, file=sys.stderr)
    sys.exit(1)


def _pdf(key):
    import pdfplumber
    p = os.path.join(SRC, key)
    if not os.path.exists(p):
        fail('%s is not on disk -- run scripts/sync_archive.py --pull' % key)
    return pdfplumber.open(p)


def _rows(words, tol=2.0):
    rows = []
    for w in sorted(words, key=lambda w: (w['top'], w['x0'])):
        if rows and abs(w['top'] - rows[-1][0]['top']) <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    for r in rows:
        r.sort(key=lambda w: w['x0'])
    return rows


def _money(t):
    t = t.strip().lstrip('$')
    if re.match(r'^\d{1,3}(?:,\d{3})*(?:\.\d\d)?$', t):
        return round(float(t.replace(',', '')), 2)
    return None


# ===================================================================== Harvard
HEADER_WORDS = {'SCHOOL', 'SCHOOL-', 'NON-', 'NON', 'TEACHER', 'TEACHER-', 'YEAR', 'SUBSTITUES'}


def harvard():
    """[(section, name, amount)], {section: printed DEPT TOTAL}, refused count."""
    key, pages = HARVARD
    pdf = _pdf(key)
    recs, totals, refused = [], {}, 0
    section, label = None, []
    for pn in pages:
        page = pdf.pages[pn - 1]
        mid = page.width / 2.0
        words = page.extract_words()
        for col in (0, 1):
            ws = [w for w in words if (w['x0'] >= mid) == bool(col) and w['top'] > 90
                  and w['top'] < page.height - 40]
            x_amt = (mid if col else 0) + 160      # the GROSS $ column sits right of this
            last = None
            for row in _rows(ws):
                text = ' '.join(w['text'] for w in row)
                if text.startswith('LAST NAME'):
                    section = ' '.join(label) if label else section
                    label, last = [], None
                    continue
                if text.startswith('DEPT TOTAL'):
                    amt = _money(row[-1]['text'])
                    if amt is None:
                        fail('Harvard p%d: a DEPT TOTAL with no amount' % pn)
                    totals[section] = amt
                    last = None
                    continue
                amts = [(w, _money(w['text'])) for w in row if w['x0'] >= x_amt]
                amts = [(w, a) for w, a in amts if a is not None]
                if amts:
                    w, a = amts[-1]
                    name = [x['text'] for x in row if x is not w]
                    if not name:
                        refused += 1
                        continue
                    last = [section, name, a, pn, row[0]['top']]
                    recs.append(last)
                    continue
                if all(w['text'] in HEADER_WORDS for w in row):
                    label.append(text)
                    continue
                # A wrapped name (a hyphenated surname split over two lines): a row of name words, no amount,
                # directly under a record.
                if last is not None and row[0]['top'] - last[4] < 16:
                    last[1] = last[1] + [w['text'] for w in row]
                    continue
                refused += 1
    return [(s, ' '.join(n), a, p) for s, n, a, p, _t in recs], totals, refused


# ===================================================================== Ashburnham-Westminster
TEACHING_TITLES = {
    'KINDERGARTEN', '1ST GRADE', '2ND GRADE', '3RD GRADE', '4TH GRADE', '5TH GRADE',
    'EARLY CHILDHOOD', '7TH GRADE SCIENCE',
    'MATH', 'SCIENCE', 'SOCIAL STUDIES', 'ENGLISH', 'ENGLISH/LANGUAGE', 'FOREIGN LANGUAGE',
    'ART', 'MUSIC', 'PHYSICAL EDUCATION', 'HEALTH/FITNESS', 'HEALTH', 'TECHNOLOGY',
    'DIGITAL LITERACY', 'BUSINESS', 'SPECIAL ED TEACHER', 'TEACHER', 'LIBRARIAN/MEDIA',
}
PROGRAMME_TITLES = {'ACHIEVE', 'ACE', 'EXCEL'}


def _title(t):
    # The text layer splits HEALTH as `HEAL TH` (a ligature); nothing else is altered.
    return ' '.join(t.replace('HEAL TH', 'HEALTH').split())


def aw():
    """[(title, name, amount, page)], refused count, heading seen on every page."""
    key, pages = AW
    pdf = _pdf(key)
    recs, refused, headed = [], 0, 0
    for pn in pages:
        page = pdf.pages[pn - 1]
        words = page.extract_words()
        if AW_HEADING in ' '.join(w['text'] for w in words):
            headed += 1
        hp = [w for w in words if w['text'] == 'PRIMARY']
        hg = [w for w in words if w['text'] == 'GROSS']
        if len(hp) != 1 or len(hg) != 1:
            fail('A-W p%d: the column header is not printed once' % pn)
        # Below the header's own line: the first record sits a fraction above its bottom edge.
        x_title, x_amt, top = hp[0]['x0'] - 3, hg[0]['x0'] - 10, hp[0]['top'] + 3
        ndollar = sum(1 for w in words if w['text'].startswith('$') and w['top'] > top)
        nrec, nseen = 0, 0
        for row in _rows([w for w in words if w['top'] > top]):
            name = [w['text'] for w in row if w['x0'] < x_title]
            title = [w['text'] for w in row if x_title <= w['x0'] < x_amt]
            amt = [_money(w['text']) for w in row if w['x0'] >= x_amt]
            nseen += sum(1 for w in row if w['text'].startswith('$'))
            if len(amt) == 1 and amt[0] is not None and name and title:
                recs.append((_title(' '.join(title)), ' '.join(name), amt[0], pn))
                nrec += 1
            elif name or amt:
                # (the running footer -- report title and page number -- has neither)
                refused += 1
        # EVERY AMOUNT ON THE PAGE IS ACCOUNTED FOR: in a record, or in a refused row.
        if nseen != ndollar or nrec > ndollar:
            fail('A-W p%d: %d amounts printed, %d seen in rows, %d records'
                 % (pn, ndollar, nseen, nrec))
    return recs, refused, headed


# ===================================================================== Tyngsborough
# OUR RULE over the printed POSITION, mirroring A-W's: classroom (regular education,
# kindergarten, preschool), special education and English-learner TEACHERS. Positions print a
# school code after a dash (TES, TMS, THS, ECC, DW), and spelling and case vary ("Reg Ed Teach",
# "REG ED TEACHER"), so the rule is a pattern over the upper-cased position. Title 1 teachers
# (a programme, the counterpart of A-W's reading specialists) are left out and counted, as are
# long-term substitutes, counsellors, therapists, nurses, paras and coaches.
TYNG_TEACH = re.compile(r'^(REG ED|SPED|KINDERGARTEN|PRESCHOOL|ELL) TEACH(ER)?$')
TYNG_PROGRAMME = re.compile(r'^TITLE 1 TEACH(ER)?$')


def _tyng_position(t):
    """The position without its school code: `Reg Ed Teach- TES` -> `REG ED TEACH`."""
    return ' '.join(re.split(r'\s*-\s*(?:ECC|TES|TMS|THS|DW|ECC/TES)$', t.strip().upper())[0].split())


def tyngsborough():
    """[(position, department, total, page)], refused count, {check: count}.

    The report is ONE sheet printed across two runs of pages: pdf pages 1-13 carry Department
    and Name, pages 14-26 Position, SR, Munis and Total, row for row in the same order. Rows
    are paired by page and order, and the pairing is asserted -- every page pair has the same
    number of rows. NAMES ARE NEVER READ: the department is the words left of the Name column
    header, and that is all this function takes from the first run.
    """
    key, left, right = TYNG
    pdf = _pdf(key)
    recs, refused = [], 0
    checks = collections.Counter()
    cols = None
    for pl, pr in zip(left, right):
        lp, rp = pdf.pages[pl - 1], pdf.pages[pr - 1]
        lw, rw = lp.extract_words(), rp.extract_words()
        hn = [w for w in lw if w['text'] == 'Name']
        hp = {w['text']: w for w in rw if w['text'] in ('Position', 'SR', 'Munis', 'Total')}
        # The header is printed on the FIRST page of each run only; its columns hold for the
        # rest (the sheet was printed from one spreadsheet).
        if pl == left[0]:
            if len(hn) != 1 or len(hp) != 4:
                fail('Tyngsborough p%d/p%d: the column headers are not printed once' % (pl, pr))
            cols = (hn[0]['x0'] - 3, hp['SR']['x0'] - 3, hp['Munis']['x0'] - 3,
                    hp['Total']['x0'] - 3)
            top_l, top_r = hn[0]['bottom'], hp['Position']['bottom']
        else:
            if hn or hp:
                fail('Tyngsborough p%d/p%d: a header repeated mid-report' % (pl, pr))
            top_l = top_r = 0
        x_name, x_sr, x_mu, x_to = cols
        lrows = [r for r in _rows([w for w in lw if w['top'] > top_l])]
        rrows = [r for r in _rows([w for w in rw if w['top'] > top_r])]
        if len(lrows) != len(rrows):
            fail('Tyngsborough p%d/p%d: %d rows against %d -- the pairing fails'
                 % (pl, pr, len(lrows), len(rrows)))
        checks['page_pairs'] += 1
        for lr, rr in zip(lrows, rrows):
            dept = ' '.join(w['text'] for w in lr if w['x0'] < x_name)
            pos = ' '.join(w['text'] for w in rr if w['x0'] < x_sr)

            def col(a, b):
                ts = [w['text'] for w in rr if a <= w['x0'] < b and w['text'] != '$']
                if ts == ['-']:
                    return 0.0
                return _money(ts[0]) if len(ts) == 1 else None
            sr, mu, to = col(x_sr, x_mu), col(x_mu, x_to), col(x_to, 10 ** 4)
            if None in (sr, mu, to):
                refused += 1
                continue
            # AN IDENTITY THE LIST STATES ABOUT ITSELF: Total is SR plus Munis.
            if abs(sr + mu - to) > 0.005:
                fail('Tyngsborough p%d: SR %.2f + Munis %.2f is not Total %.2f' % (pr, sr, mu, to))
            checks['rows_tied'] += 1
            recs.append((pos, dept, to, pr))
    return recs, refused, checks


# ===================================================================== aggregates
def pct(xs, q):
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def bands(values, lo_edge, hi_edge, width):
    """Counts in bands, empty tails dropped and thin tails merged inward until each end band
    holds MIN_CELL people (the rule extract_teacher_pay.py uses)."""
    bs = [(None, lo_edge)] + [(a, a + width) for a in range(lo_edge, hi_edge, width)] + \
        [(hi_edge, None)]
    cs = [sum(1 for v in values if (lo is None or v >= lo) and (hi is None or v < hi))
          for lo, hi in bs]
    while cs and cs[0] == 0:
        del bs[0], cs[0]
    while cs and cs[-1] == 0:
        del bs[-1], cs[-1]
    bs[0] = (None, bs[0][1])
    bs[-1] = (bs[-1][0], None)
    while len(bs) > 2 and 0 < cs[0] < MIN_CELL:
        bs[1] = (None, bs[1][1])
        cs[1] += cs[0]
        del bs[0], cs[0]
    while len(bs) > 2 and 0 < cs[-1] < MIN_CELL:
        bs[-2] = (bs[-2][0], None)
        cs[-2] += cs[-1]
        del bs[-1], cs[-1]
    return [('%s-%s' % ('' if lo is None else lo, '' if hi is None else hi), c)
            for (lo, hi), c in zip(bs, cs)]


def ma_top(district, fy, lane):
    """(top cell, step, page) of one lane in one fiscal year, from our table of the contracts."""
    cells = [r for r in csv.DictReader(open(SCHEDULES, encoding='utf-8'))
             if r['district'] == district and int(r['fy']) == fy and r['lane'] == lane]
    if not cells:
        fail('no %s %s schedule for FY%d in teacher-salary-schedules.csv' % (district, lane, fy))
    top = max(cells, key=lambda r: int(r['step']))
    return int(top['salary']), int(top['step']), top['page'], top['doc']


def ma_top_held(district, fy):
    """The master's-lane top cell for one fiscal year, or None if our table holds none."""
    cells = [r for r in csv.DictReader(open(SCHEDULES, encoding='utf-8'))
             if r['district'] == district and int(r['fy']) == fy and r['lane'] in MA_LANES]
    lanes = {r['lane'] for r in cells}
    if len(lanes) > 1:
        fail('%s FY%d: more than one master\'s lane name (%s)' % (district, fy, sorted(lanes)))
    if not cells:
        return None
    return ma_top(district, fy, lanes.pop())


def distribution(put, d, period, pay, how):
    """The shared measures of one selected list. Returns the full-year amounts."""
    med_all = statistics.median(pay)
    cut = PART_YEAR * med_all
    full = sorted(a for a in pay if a >= cut)
    put(d, period, 'selected', len(pay), 'people', how)
    put(d, period, 'part_year', len(pay) - len(full), 'people',
        'gross below half the selected median ($%s), our rule' % format(round(cut), ','))
    put(d, period, 'full_year', len(full), 'people', 'selected, at or above that line')
    if len(full) < MIN_CELL:
        fail('%s: fewer than %d full-year teachers' % (d, MIN_CELL))
    put(d, period, 'median', round(statistics.median(full), 2), 'dollars', 'gross pay, full-year')
    put(d, period, 'p25', round(pct(full, 0.25), 2), 'dollars', 'lower quartile')
    put(d, period, 'p75', round(pct(full, 0.75), 2), 'dollars', 'upper quartile')
    for lab, c in bands(full, BAND_LO, BAND_HI, BAND):
        put(d, period, 'band', c, 'people', lab)
    return full


def on_scale(put, d, period, full, top, note):
    """Gross pay as a share of the district's own master's top: the comparable measure."""
    shares = [100.0 * a / top for a in full]
    put(d, period, 'ma_top', top, 'dollars', note)
    put(d, period, 'at_or_above_top', sum(1 for s in shares if s >= 100), 'people',
        'full-year teachers paid at least 100% of their own district\'s master\'s top')
    put(d, period, 'at_or_above_90', sum(1 for s in shares if s >= 90), 'people',
        'full-year teachers paid at least 90% of it')
    put(d, period, 'median_pct_of_top', round(statistics.median(shares), 1), 'percent',
        'median gross pay as a share of it')
    put(d, period, 'p25_pct_of_top', round(pct(shares, 0.25), 1), 'percent', 'lower quartile')
    put(d, period, 'p75_pct_of_top', round(pct(shares, 0.75), 1), 'percent', 'upper quartile')
    for lab, c in bands(shares, PCT_LO, PCT_HI, PCT_BAND):
        put(d, period, 'pct_band', c, 'people', lab)


def aggregates():
    out = []

    def put(d, period, measure, value, unit, note=''):
        out.append({'district': d, 'period': period, 'measure': measure,
                    'value': ('%.2f' % value if isinstance(value, float) else value),
                    'unit': unit, 'note': note})

    # ---------------------------------------------------------------- Lunenburg, from its own
    import extract_teacher_pay as XP
    rows, _ = XP.wage_list(2025)
    found, _, _ = XP.match(2025, rows)
    lpay = [rows[i]['amt'] for i in found.values()]
    P = 'calendar 2025'
    full = distribution(put, 'Lunenburg', P, lpay,
                        'roster teachers matched by name to the town\'s wage list '
                        '(extract_teacher_pay.py)')
    t25, s, pg, _ = ma_top('Lunenburg', 2025, 'Masters')
    t26, _, pg26, _ = ma_top('Lunenburg', 2026, 'Masters')
    on_scale(put, 'Lunenburg', P, full, round((t25 + t26) / 2.0),
             'Masters step %d: half the FY2025 cell ($%s, p%s) plus half the FY2026 ($%s, '
             'p%s), our blend' % (s, format(t25, ','), pg, format(t26, ','), pg26))

    # ---------------------------------------------------------------- Harvard
    recs, totals, refused = harvard()
    secs = collections.defaultdict(list)
    for sec, _n, a, _p in recs:
        secs[sec].append(a)
    for sec in sorted(secs):
        got = round(sum(secs[sec]), 2)
        if sec not in totals or abs(got - totals[sec]) > 0.005:
            fail('Harvard section %r: rows sum to %.2f, the page prints %s'
                 % (sec, got, totals.get(sec)))
    TEACH = 'SCHOOL TEACHER'
    if TEACH not in secs:
        fail('Harvard: no SCHOOL TEACHER section read')
    P = 'period not printed'
    put('Harvard', P, 'list_rows', len(recs), 'people',
        'every row of the School Employee Earnings Report, %d sections' % len(secs))
    put('Harvard', P, 'sections_tied', len(secs), 'sections',
        'each section\'s rows sum to the DEPT TOTAL the page prints, to the cent')
    put('Harvard', P, 'rows_refused', refused, 'rows', 'a name with no amount, or the reverse')
    put('Harvard', P, 'teacher_total', totals[TEACH], 'dollars',
        'the TEACHER section\'s printed DEPT TOTAL')
    full = distribution(put, 'Harvard', P, secs[TEACH],
                        'the list\'s own SCHOOL / TEACHER section, as the town printed it')
    h25, s, pg, _ = ma_top('Harvard', 2025, 'M')
    h26, _, pg26, _ = ma_top('Harvard', 2026, 'M')
    on_scale(put, 'Harvard', 'if calendar 2025', full, round((h25 + h26) / 2.0),
             'M step %d: half the FY2025 cell ($%s, p%s) plus half the FY2026 ($%s, p%s), our '
             'blend' % (s, format(h25, ','), pg, format(h26, ','), pg26))
    on_scale(put, 'Harvard', 'if fiscal 2025', full, h25,
             'M step %d, FY2025 cell ($%s, p%s)' % (s, format(h25, ','), pg))

    # ---------------------------------------------------------------- Ashburnham-Westminster
    recs_aw, refused, headed = aw()
    P = 'fiscal 2025 (1 July 2024 to 30 June 2025)'
    if headed != len(AW[1]):
        fail('A-W: the period heading is not printed on every page')
    names = collections.Counter(n for _t, n, _a, _p in recs_aw)
    put('Ashburnham-Westminster', P, 'list_rows', len(recs_aw), 'people',
        'every row with a name, a title and an amount; earnings over $500 only')
    put('Ashburnham-Westminster', P, 'rows_refused', refused, 'rows',
        'a row missing a name, a title or an amount')
    put('Ashburnham-Westminster', P, 'names_printed_twice', sum(1 for c in names.values() if c > 1),
        'names', 'the same name on two rows (kept: no way to tell two people from one)')
    put('Ashburnham-Westminster', P, 'list_heading', AW_HEADING, 'text',
        'printed on each of the %d pages' % headed)
    sel = [a for t, _n, a, _p in recs_aw if t in TEACHING_TITLES]
    prog = [a for t, _n, a, _p in recs_aw if t in PROGRAMME_TITLES]
    put('Ashburnham-Westminster', P, 'programme_titles_left_out', len(prog), 'people',
        'ACHIEVE, ACE, EXCEL: a programme, not a post')
    titles = sorted({t for t, _n, _a, _p in recs_aw if t in TEACHING_TITLES})
    put('Ashburnham-Westminster', P, 'teaching_titles', len(titles), 'titles',
        '; '.join(titles))
    full = distribution(put, 'Ashburnham-Westminster', P, sel,
                        'our rule over the printed primary job title (TEACHING_TITLES)')
    held = ma_top_held('Ashburnham-Westminster', 2025)
    if held:
        t, st, pg, _ = held
        on_scale(put, 'Ashburnham-Westminster', P, full, t,
                 'master\'s lane step %d, FY2025 cell ($%s, p%s)' % (st, format(t, ','), pg))
    else:
        put('Ashburnham-Westminster', P, 'ma_top', '', 'dollars',
            'not held for FY2025: the agreements held cover FY2017-FY2019 and FY2026-FY2028')

    # ---------------------------------------------------------------- Tyngsborough
    recs_ty, refused, checks = tyngsborough()
    P = 'period not printed; titled %d' % TYNG_YEAR
    D = 'Tyngsborough'
    put(D, P, 'list_rows', len(recs_ty), 'people',
        'every row with three amounts, town and school, paired across the two runs of pages')
    put(D, P, 'rows_tied', checks['rows_tied'], 'rows',
        'each row\'s Total is its SR plus its Munis amount, to the cent')
    put(D, P, 'rows_refused', refused, 'rows', 'a row whose amounts would not read')
    put(D, P, 'positions_blank', sum(1 for p_, _d, _a, _p in recs_ty if not p_), 'rows',
        'a row with amounts and no position printed (not selected)')
    sel_ty = [(p_, d_, a_) for p_, d_, a_, _p in recs_ty if TYNG_TEACH.match(_tyng_position(p_))]
    if any(not d_.startswith('School') for _p, d_, _a in sel_ty):
        fail('Tyngsborough: a teaching position outside the School Dept. -- the pairing is wrong')
    put(D, P, 'programme_titles_left_out',
        sum(1 for p_, _d, _a, _p in recs_ty if TYNG_PROGRAMME.match(_tyng_position(p_))),
        'people', 'Title 1 teachers: a programme, not a post')
    pos = sorted({_tyng_position(p_) for p_, _d, _a in sel_ty})
    put(D, P, 'teaching_titles', len(pos), 'titles', '; '.join(pos))
    full = distribution(put, D, P, [a_ for _p, _d, a_ in sel_ty],
                        'our rule over the printed position, school code dropped (TYNG_TEACH)')
    h1, h2 = ma_top_held(D, TYNG_YEAR), ma_top_held(D, TYNG_YEAR + 1)
    if h1 and h2:
        on_scale(put, D, 'if calendar %d' % TYNG_YEAR, full, round((h1[0] + h2[0]) / 2.0),
                 'master\'s step %d: half the FY%d cell ($%s, p%s) plus half the FY%d ($%s, '
                 'p%s), our blend' % (h1[1], TYNG_YEAR, format(h1[0], ','), h1[2],
                                      TYNG_YEAR + 1, format(h2[0], ','), h2[2]))
    else:
        put(D, P, 'ma_top', '', 'dollars',
            'not held for FY%d-FY%d: the agreements held cover FY2019-FY2021 and FY2025-FY2027'
            % (TYNG_YEAR, TYNG_YEAR + 1))
    return out, recs, recs_aw, recs_ty


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def write_private(recs, recs_aw, recs_ty):
    """Name-level rows -- PRIVATE, gitignored, never published."""
    os.makedirs(PRIV, exist_ok=True)
    with open(os.path.join(PRIV, 'harvard-rows.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['section', 'name', 'amount', 'page'])
        w.writerows(recs)
    with open(os.path.join(PRIV, 'aw-rows.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['title', 'name', 'amount', 'page', 'teacher'])
        w.writerows([(t, n, a, p, t in TEACHING_TITLES) for t, n, a, p in recs_aw])
    # Tyngsborough: no names were read, but the rows stay private all the same -- a position
    # and a school code can name one person.
    with open(os.path.join(PRIV, 'tyngsborough-rows.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['position', 'department', 'total', 'page', 'teacher'])
        w.writerows([(p_, d_, a_, pg, bool(TYNG_TEACH.match(_tyng_position(p_))))
                     for p_, d_, a_, pg in recs_ty])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, recs, recs_aw, recs_ty = aggregates()
    text = render(rows)
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        if cur != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('peer teacher pay: current (%d rows)' % (text.count('\n') - 1))
        return 0
    write_private(recs, recs_aw, recs_ty)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
