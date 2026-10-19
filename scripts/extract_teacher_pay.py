#!/usr/bin/env python3
"""Teacher gross pay, by year, as a DISTRIBUTION -- from the town's own wage list and rosters.

    python3 scripts/extract_teacher_pay.py            # read, match, write the aggregates
    python3 scripts/extract_teacher_pay.py --ocr      # ...re-reading every wage page first
    python3 scripts/extract_teacher_pay.py --check    # fail if the aggregates would change

THE QUESTION (TJ, 19 October 2026). DESE's average teacher salary puts Lunenburg second of
the six districts this project compares, while residents say Lunenburg's PAY SCALE is the
lowest. Both can be true if Lunenburg's teachers sit higher on the scale. Nobody publishes
how many teachers are on each step -- *"seems like hidden data to lean on if they dont
publish anything."*

THE HIDDEN DATA. Every annual town report, FY2011 to FY2025, prints the TOWN AND SCHOOL
employee gross wages for the CALENDAR year (the heading says so: "CALENDAR 2011 WAGES",
"Town & School Employee Calendar 2018 Gross Wages", "Calendar Year 2022 Gross Wages"), every
person by name. The same reports print the schools' staff rosters by name and post, which
`build_staff_rosters.py` has already read into `sources/data/staff-roster-entries.csv`.
Joining the two by name gives each roster teacher's gross pay; the distribution of that pay
is the nearest thing to a step-and-lane count that anything published can give.

PRIVACY -- RULE 13e. The town printed every name and amount. THIS PROJECT PUBLISHES NO
PER-PERSON PAY. Everything name-level -- the OCR, the wage rows, the match -- is written
under `build/private/teacher-pay/`, which is gitignored (`build/`), and only COUNTS and
DISTRIBUTIONS leave this script, in `sources/data/teacher-pay-distribution.csv`. The
aggregate refuses to write a histogram band, or any statistic, resting on fewer than
MIN_CELL people, so no single person's pay can be read back out of it.

WHY A NEW READER. `extract_gross_wages.py` reads the same pages off the line-level OCR cache
and gets most of six years and little of the rest (on 19 October 2026: FY2018 121 rows of
about 586 printed, FY2022 39, FY2023 1, FY2024 39). The pages are clean; the instrument
fails. Vision's ACCURATE level, handed a whole wage page, returns a fraction of its cells --
100 observations for 282 on FY2024 pdf page 188 -- while its FAST level returns 282. So this
reader renders each page (`scripts/ocr_strips.swift`), turns it upright by its MEASURED
rotation (rule 13b), reads it at both levels, pairs names with amounts row by row after
taking out the residual slope it measures from the page itself, and keeps the fast reading
with the accurate one as a check on every amount both read.

WHAT IS CHECKED, since a wage page prints NO TOTAL (checked by eye on every year's pages):
  * DIGITAL YEARS are reconciled amount by amount against the page's own text layer: the
    multiset of amounts we read must equal the multiset the PDF carries. Where it does not,
    the difference is counted and printed.
  * Every year: a row is written only where a name and an amount sit in the same printed
    row on the same side of the page; an amount with no name, or a name with no amount, is
    COUNTED AND REFUSED, never attached to the nearest neighbour.

THE MATCH (logged, never fuzzy). A roster name `Jane A. Smith-Jones` and a wage name
`SMITH-JONES JANE` match when, after upper-casing and stripping punctuation and accents,
(surname, first given name) are equal. Three exact relaxations, each counted separately so
the match rate states what it rests on: a hyphenated or two-word surname may match on either
part; a middle initial is ignored; a given name may match on its first four letters where
that is unique in the year's wage list (`Kathy`/`Kathleen` does NOT match: that is a guess).
A roster name matching two wage rows is refused as ambiguous. Nothing else is tried.

THE CALENDAR OFFSET. Report FY<y> prints calendar year <y> wages and the roster printed in
the same report. A calendar year spans two contract years: January-June of FY<y> and
July-December of FY<y+1>. So calendar 2025 pay for a teacher on the top step both years is
about half the FY2025 cell plus half the FY2026 cell. That is OUR approximation -- it
assumes pay spread evenly over the months, which a 10-month teacher paid over 26 periods
roughly is and a summer lump sum is not -- and it is applied only to compare against the
schedule, never to the distribution itself.

GROSS PAY IS NOT SALARY. It includes stipends, coaching, summer work, extra duties,
retroactive pay and any back pay a settlement paid in that year. It is not the schedule cell
and is never equated with it. Pay above a top-step cell says the person was paid more than
that cell; it does not say they sit on that step.
"""
import argparse
import collections
import csv
import glob
import os
import re
import statistics
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIV = os.path.join(ROOT, 'build', 'private', 'teacher-pay')
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
TEXT = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
ROSTER = os.path.join(ROOT, 'sources', 'data', 'staff-roster-entries.csv')
SCHEDULE = os.path.join(ROOT, 'sources', 'contracts', 'data', 'lea-teacher-salary-schedule.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'teacher-pay-distribution.csv')
SWIFT = os.path.join(ROOT, 'scripts', 'ocr_strips.swift')
BIN = os.path.join(PRIV, 'bin', 'ocr_strips')
SCALE = 3

# The wage list's pdf pages, per report year -- every one opened and looked at, 19 October
# 2026 (contact sheets of the pages either side, so a page that starts or ends the list was
# seen, not inferred). FY2017 onward agree with the contents page (report-index.csv); the
# earlier contents pages do not list it, or list printed pages.
PAGES = {
    2011: ('4117-fy-2011-annual-town-report.pdf', range(98, 102)),
    2012: ('4118-fy-2012-annual-town-report.pdf', range(112, 116)),
    2013: ('4119-fy-2013-annual-town-report.pdf', range(93, 98)),
    2014: ('4120-fy-2014-annual-town-report.pdf', range(168, 174)),
    2015: ('4121-fy-2015-annual-town-report.pdf', range(206, 212)),
    2016: ('4123-fy-2016-annual-town-report.pdf', range(198, 203)),
    2017: ('4124-fy-2017-annual-town-report.pdf', range(192, 199)),
    2018: ('4125-fy-2018-annual-town-report.pdf', range(248, 255)),
    2019: ('4126-fy-2019-annual-town-report.pdf', range(197, 204)),
    2020: ('4127-fy-2020-annual-town-report.pdf', range(208, 215)),
    2021: ('4128-fy-2021-annual-town-report.pdf', range(162, 169)),
    2022: ('4129-fy-2022-annual-town-report.pdf', range(186, 193)),
    2023: ('4131-fy-2023-annual-town-report.pdf', range(190, 198)),
    2024: ('4132-fy-2024-annual-town-report.pdf', range(186, 194)),
    2025: ('4130-fy-2025-annual-town-report.pdf', range(177, 183)),
}

MONEY = re.compile(r'^\$?\s?(\d{1,3}(?:[,.]\d{3})*[.,]\d\d)$')
DEPTS = {'FIRE', 'POLICE', 'SCHOOL', 'DPW', 'LIBRARY', 'HIGHWAY', 'CEMETERY', 'WATER', 'SEWER',
         'COA', 'SENIOR', 'BUILDING', 'PARK', 'PARKS', 'RECREATION', 'TOWN', 'HALL', 'ELECTED',
         'SELECTMEN', 'ASSESSORS', 'COLLECTOR', 'TREASURER', 'CLERK', 'PLANNING', 'TECH',
         'ELECTIONS', 'ELECTION', 'ACCOUNTING', 'HEALTH', 'VET', 'VETERANS', 'CONSERVATION',
         'ANIMAL', 'CONTROL', 'TRANSFER', 'STATION', 'IT', 'BOARD', 'INSPECTOR'}


def fail(msg):
    print('extract_teacher_pay: %s' % msg, file=sys.stderr)
    sys.exit(1)


# ===================================================================== reading the pages
def _binary():
    if not os.path.exists(BIN) or os.path.getmtime(BIN) < os.path.getmtime(SWIFT):
        os.makedirs(os.path.dirname(BIN), exist_ok=True)
        subprocess.run(['swiftc', '-O', '-o', BIN, SWIFT], check=True,
                       stderr=subprocess.DEVNULL)
    return BIN


def deskew(img):
    """The page turned upright: the angle that makes its columns sharpest, MEASURED.

    A scan is slightly turned, so a ruled column's edge and a column of figures smear across
    a band of x. The angle is the one, in tenths of a degree within two degrees, that
    maximises the variance of the page's column profile -- rule 13b's measured rotation,
    found from the page itself. A digital page measures 0.0.
    """
    import numpy as np
    small = img.convert('L')
    small.thumbnail((900, 1200))
    best, angle = -1, 0.0
    for t in [x / 10.0 for x in range(-20, 21)]:
        r = small.rotate(t, fillcolor=255)
        prof = (np.asarray(r) < 140).sum(0).astype(float)
        v = prof.var()
        if v > best:
            best, angle = v, t
    return (img.rotate(angle, fillcolor=255, resample=3) if angle else img), angle




def ocr_year(fy):
    """Render, turn upright, and read every wage page of one year into the private cache.

    Also records, per page, what the PDF itself is -- `pdf_kind.classify()` (rule 13d: a
    page is a scan only if its structure says so) -- and the page's own text layer, which
    is what the digital years are reconciled against.
    """
    from PIL import Image
    import pdf_kind
    doc, pages = PAGES[fy]
    pdf = os.path.join(DOCS, doc)
    if not os.path.exists(pdf):
        fail('%s is not on disk -- run scripts/sync_archive.py --pull' % doc)
    d = os.path.join(PRIV, 'pages', str(fy))
    os.makedirs(d, exist_ok=True)
    subprocess.run([_binary(), 'render', pdf, str(min(pages)), str(max(pages)), str(SCALE), d],
                   check=True)
    k = pdf_kind.classify(pdf)
    texts = dict(re.findall(r'===PAGE (\d+)===\n(.*?)(?=\n===PAGE \d+===|\Z)', k['text'], re.S))
    meta = []
    ups = []
    for p in pages:
        img, angle = deskew(Image.open(os.path.join(d, 'p%d.png' % p)).convert('RGB'))
        up = os.path.join(d, 'p%d.upright.png' % p)
        img.save(up)
        ups.append(up)
        kind = k['pages'][p - 1]
        meta.append('%d\t%s\t%.1f\t%s' % (p, kind['kind'], angle, kind['dpi'] or ''))
        with open(os.path.join(d, 'p%d.textlayer.txt' % p), 'w', encoding='utf-8') as fh:
            fh.write(texts.get(str(p), ''))
    with open(os.path.join(d, 'pages.tsv'), 'w') as fh:
        fh.write('page\tkind\tangle\tdpi\n' + '\n'.join(meta) + '\n')
    subprocess.run([_binary(), 'ocr'] + ups, check=True)


# ===================================================================== parsing the reads
OCR_DIGIT = str.maketrans({'I': '1', 'l': '1', '|': '1', 'O': '0', 'o': '0'})


def _amount(t):
    t = t.strip().replace(' ', '')
    # A money token with a letter Vision mistook for a digit -- `I,000.00` on FY2024 page
    # 188. Only I, l, | and O are mapped, and only where the token already has a money
    # shape with at least three real digits; anything else is not an amount.
    if re.match(r'^\$?[\dIl|Oo,.]+$', t) and len(re.findall(r'\d', t)) >= 3:
        t = t.translate(OCR_DIGIT)
    m = MONEY.match(t)
    if not m:
        return None
    digits = re.sub(r'[^\d]', '', m.group(1))
    return int(digits) / 100.0


def _obs(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as fh:
        next(fh)
        for line in fh:
            f = line.rstrip('\n').split('\t')
            if len(f) < 6:
                continue
            out.append({'x': float(f[0]), 'y': float(f[1]), 'w': float(f[2]),
                        't': '\t'.join(f[5:]).strip()})
    return out


def _cells(obs):
    """Split an observation into cells: a money token is always its own cell."""
    out = []
    for o in obs:
        toks = o['t'].split()
        if not toks:
            continue
        # `1,190.04;,SCHOOL` -- an amount and the department after it read as one token.
        split = []
        for t in toks:
            m = re.match(r'^(\$?[\dIl|Oo,.]*\d[.,]\d\d)[^\d](.+)$', t)
            if m and _amount(m.group(1)) is not None:
                split += [m.group(1), m.group(2).strip(';:,.\'|')]
            else:
                split.append(t)
        toks = [t for t in split if t]
        n = sum(len(t) + 1 for t in toks)
        at, buf, bx = 0, [], None
        for t in toks:
            x = o['x'] + o['w'] * at / float(n)
            at += len(t) + 1
            if _amount(t) is not None or t == '$':
                if buf:
                    out.append({'x': bx, 'y': o['y'], 't': ' '.join(buf)})
                    buf = []
                if t != '$':
                    out.append({'x': x, 'y': o['y'], 't': t, 'amt': _amount(t)})
                continue
            if not buf:
                bx = x
            buf.append(t)
        if buf:
            out.append({'x': bx, 'y': o['y'], 't': ' '.join(buf)})
    return out


def _slope(cells):
    """The page's residual rotation: the MEDIAN slope from each cell to its nearest
    neighbour to the right in the same printed row (rule 13b -- measure it, do not fight it)."""
    sl = []
    for c in cells:
        right = [d for d in cells if 0.03 < d['x'] - c['x'] < 0.3 and abs(d['y'] - c['y']) < 0.008]
        if right:
            d = min(right, key=lambda d: d['x'] - c['x'])
            sl.append((d['y'] - c['y']) / (d['x'] - c['x']))
    return statistics.median(sl) if len(sl) >= 20 else 0.0


def _rows(cells):
    """Printed rows, banded at HALF the page's own median row pitch (rule 13b), after
    taking out the measured rotation."""
    k = _slope(cells)
    for c in cells:
        c['y'] = c['y'] - k * c['x']
    ys = sorted({round(c['y'], 4) for c in cells if 'amt' in c}, reverse=True)
    gaps = sorted(a - b for a, b in zip(ys, ys[1:]) if 0.004 < a - b < 0.05)
    band = gaps[len(gaps) // 2] / 2.0 if gaps else 0.006
    rows = []
    for c in sorted(cells, key=lambda c: -c['y']):
        if rows and abs(c['y'] - rows[-1][0]['y']) < band:
            rows[-1].append(c)
        else:
            rows.append([c])
    for r in rows:
        r.sort(key=lambda c: c['x'])
    return rows


# The list prints a department beside each name through calendar 2017 and not after. A
# department word is looked for only in those years, because later a surname -- HALL --
# would be read as one and dropped from the name.
LAST_DEPT_YEAR = 2017


def _isdept(w):
    t = re.sub(r'[^A-Z ]', '', w.upper().replace('FI RE', 'FIRE')).split()
    return bool(t) and all(x in DEPTS for x in t)


HEADING = re.compile(r'gross wages|calendar|wages|^page \d+$|^\d{1,3}$', re.I)


def records(obs, depts=True):
    """(name parts, department, amount, x, y) per printed record, and the refusals.

    A record is the run of name cells that ends at an amount, within one printed row. A
    row whose cells do not end in an amount leaves a name with no amount; a run of two
    amounts leaves an amount with no name. Both are counted and refused.
    """
    recs, refused = [], 0
    for row in _rows(_cells(obs)):
        if all(HEADING.search(c['t']) for c in row if 'amt' not in c) and \
                not any('amt' in c for c in row):
            continue
        buf = []
        for c in row:
            # FY2014-FY2017 print the department AFTER the amount: a department word that
            # follows an amount belongs to the record that amount closed.
            if depts and not buf and recs and 'amt' not in c and _isdept(c['t']) and \
                    recs[-1].get('row') is row and not recs[-1]['dept']:
                recs[-1]['dept'] = ' '.join(re.sub(r'[^A-Z ]', '', c['t'].upper()).split())
                continue
            if 'amt' in c:
                words = [b['t'] for b in buf if not HEADING.search(b['t'])]
                dept = [w for w in words if depts and _isdept(w)]
                names = [w for w in words if w not in dept]
                if not names:
                    refused += 1
                else:
                    recs.append({'parts': names, 'amt': c['amt'],
                                 'dept': ' '.join(re.sub(r'[^A-Z ]', '', ' '.join(dept).upper())
                                                  .split()),
                                 'x': c['x'], 'y': c['y'], 'row': row})
                buf = []
            else:
                buf.append(c)
        if [b for b in buf if not HEADING.search(b['t'])]:
            refused += 1
    return recs, refused


def read_page(fy, p):
    """One page's records: the FAST reading, with each amount checked against ACCURATE.

    FAST is the complete reading (see ocr_strips.swift) and ACCURATE the careful one where
    it reads at all. Where both read an amount at the same place they must agree, or the
    record is marked `disagree`; on a digital page the text layer then decides.
    """
    d = os.path.join(PRIV, 'pages', str(fy))
    dep = fy <= LAST_DEPT_YEAR
    fast, fref = records(_obs(os.path.join(d, 'p%d.upright.png.fast.tsv' % p)), dep)
    acc, aref = records(_obs(os.path.join(d, 'p%d.upright.png.acc.tsv' % p)), dep)
    for r in fast:
        near = [a for a in acc if abs(a['y'] - r['y']) < 0.004 and abs(a['x'] - r['x']) < 0.03]
        r['check'] = 'fast only'
        if near:
            a = near[0]
            if abs(a['amt'] - r['amt']) < 0.005:
                r['check'] = 'both readings agree'
            else:
                r['check'] = 'disagree'
                r['alt'] = a['amt']
            # the careful reading's NAME where it has one: fast mode drops accents and
            # hyphens more often than accurate does
            if len(' '.join(a['parts'])) >= len(' '.join(r['parts'])) - 1:
                r['parts'] = a['parts']
    return fast, fref


def textlayer_amounts(fy, p):
    t = open(os.path.join(PRIV, 'pages', str(fy), 'p%d.textlayer.txt' % p),
             encoding='utf-8').read()
    return [int(re.sub(r'\D', '', m)) / 100.0
            for m in re.findall(r'(?<![\d,.])\d{1,3}(?:,\d{3})*\.\d\d(?![\d])', t)]


def wage_list(fy):
    """Every record of one year's list, with the reconciliation that can be stated for it."""
    meta = {}
    path = os.path.join(PRIV, 'pages', str(fy), 'pages.tsv')
    if not os.path.exists(path):
        fail('no private reading of FY%d -- run with --ocr (needs the PDFs and swift)' % fy)
    for r in csv.DictReader(open(path), delimiter='\t'):
        meta[int(r['page'])] = r
    rows, stats = [], collections.Counter()
    for p in PAGES[fy][1]:
        recs, refused = read_page(fy, p)
        stats['refused'] += refused
        tl = textlayer_amounts(fy, p)
        kind = meta[p]['kind']
        stats['pages_' + kind.replace(' ', '_').replace('+', '_')] += 1
        if tl and kind in ('text', 'text+image'):
            # Reconcile the multiset of amounts, both ways.
            ours = collections.Counter(round(r['amt'], 2) for r in recs)
            theirs = collections.Counter(round(a, 2) for a in tl)
            stats['tl_amounts'] += sum(theirs.values())
            stats['tl_agree'] += sum((ours & theirs).values())
            stats['tl_ours_only'] += sum((ours - theirs).values())
            stats['tl_theirs_only'] += sum((theirs - ours).values())
            for r in recs:
                if r['check'] == 'disagree' and theirs.get(round(r['alt'], 2)) and \
                        not theirs.get(round(r['amt'], 2)):
                    r['amt'] = r['alt']
                    r['check'] = 'text layer decided'
        for r in recs:
            stats['check_' + r['check'].replace(' ', '_')] += 1
            r['page'] = p
            rows.append(r)
    # THE TOWN PRINTED SOME ROWS TWICE. FY2023 pdf page 197 reprints the right-hand column
    # of page 196 (T to Z), and FY2016 page 202 the tail of page 201 (T to W) -- both seen
    # on the page images, 19 October 2026. A row whose name and
    # amount are both identical to an earlier row is dropped and counted; two different
    # people with the same name AND the same pay to the cent is not a case worth keeping
    # a duplicate for.
    seen, kept = set(), []
    for r in rows:
        k = (norm(' '.join(r['parts'])), round(r['amt'], 2))
        if k in seen:
            stats['printed twice, dropped'] += 1
            continue
        seen.add(k)
        kept.append(r)
    rows = kept
    stats['rows'] = len(rows)
    stats['total'] = round(sum(r['amt'] for r in rows), 2)
    return rows, stats


# ===================================================================== the roster's teachers
TEACHER_POSITIONS = {'Classroom Teacher', 'Specialist Teacher', 'Special Education Teacher'}
# OUR RULE for a roster line `classify_roster_roles.py` left unclassified: a line printed
# under a grade-level or subject-area heading with no title of its own, or titled with a
# kindergarten room (`K1`) or STEM. These are the teachers' lines on the FY2024 and FY2025
# middle-school rosters (`8th Grade:`, `Unified Arts`). Counted separately.
BLANK_TEACHER = re.compile(r'\b(\d+th|\dst|\dnd|\drd|Ith) Grade\b|Unified Arts|Special Areas',
                           re.I)
BLANK_TEACHER_ROLE = re.compile(r'^(K\d|STEM|Teacher)$', re.I)


def roster_teachers(fy):
    """{normalised name: (given, surname, how)} -- each teacher once, however many lines."""
    out = {}
    for r in csv.DictReader(open(ROSTER, encoding='utf-8')):
        if int(r['fy']) != fy:
            continue
        how = None
        if r['position'] in TEACHER_POSITIONS:
            how = 'classified teacher'
        elif not r['position'] and (BLANK_TEACHER.search(r['grade_or_dept']) or
                                    BLANK_TEACHER_ROLE.match(r['role_raw'].strip())):
            how = 'unclassified line under a teaching heading (our rule)'
        if not how:
            continue
        toks = [t for t in re.split(r'\s+', re.sub(r'[*,()]', ' ', r['name']).strip()) if t]
        toks = [t for t in toks if not re.match(r'^(jr|sr|ii|iii|mrs?|ms|dr)\.?$', t, re.I)]
        if len(toks) < 2:
            continue
        given = toks[0]
        rest = [t for t in toks[1:] if not re.match(r'^[A-Za-z]\.?$', t)]   # middle initial
        if not rest:
            continue
        key = norm(given) + '|' + norm(' '.join(rest))
        out.setdefault(key, (given, ' '.join(rest), how))
    return out


def norm(s):
    s = unicodedata.normalize('NFKD', s)
    return re.sub(r'[^A-Z]', '', s.upper())


def wage_names(r):
    """(surname, given names) of a wage row. FY2011 prints `SURNAME, GIVEN` in one cell."""
    parts = list(r['parts'])
    if len(parts) == 1 and ',' in parts[0]:
        a, b = parts[0].split(',', 1)
        return a.strip(), b.strip().split()
    if len(parts) == 1:
        toks = parts[0].split()
        return (toks[0], toks[1:]) if len(toks) > 1 else (toks[0] if toks else '', [])
    return parts[0], ' '.join(parts[1:]).split()


def match(fy, rows):
    """Each roster teacher's wage row, by the logged rules. Returns (matches, stats)."""
    idx = collections.defaultdict(list)
    for i, r in enumerate(rows):
        sur, given = wage_names(r)
        r['_sur'], r['_given'] = norm(sur), [norm(g) for g in given]
        r['_surparts'] = {norm(x) for x in re.split(r'[-\s]+', sur) if norm(x)}
        idx[r['_sur']].append(i)
    teachers = roster_teachers(fy)
    stats = collections.Counter()
    found = {}
    def first(r):
        # `TI MOTHY`, `KRI STEN`: a given name the reader split. Where the first piece is
        # two letters or fewer, the pieces are joined -- letters only, nothing guessed.
        g = r['_given']
        if not g:
            return ''
        return ''.join(g[:2]) if len(g) > 1 and len(g[0]) <= 2 else g[0]

    def find(given, sur):
        g, s = norm(given), norm(sur)
        sparts = {norm(x) for x in re.split(r'[-\s]+', sur) if norm(x)}
        rules = [
            ('exact surname and first given name',
             lambda: [i for i in idx.get(s, []) if first(rows[i]) == g]),
            ('one part of a hyphenated or two-word surname',
             lambda: [i for i, r in enumerate(rows)
                      if (sparts & r['_surparts']) and (len(sparts) > 1 or len(r['_surparts']) > 1)
                      and first(r) == g]),
            ('surname, and the given name a prefix of the printed one (Jen, Jennifer), unique',
             lambda: [i for i in idx.get(s, []) if len(g) >= 3 and first(rows[i]).startswith(g)]
             if len([i for i in idx.get(s, []) if first(rows[i]).startswith(g)]) == 1 else []),
            ('surname, and the first four letters of the given name, unique',
             lambda: [i for i in idx.get(s, []) if first(rows[i])[:4] == g[:4]]
             if len(g) >= 4 else []),
        ]
        for rule, f in rules:
            c = f()
            if c:
                return rule, c
        return None, []

    for key, (given, sur, how) in sorted(teachers.items()):
        stats['roster ' + how] += 1
        rule, cand = find(given, sur)
        # SOME ROSTERS PRINT THE SURNAME FIRST (FY2020 has dozens). Tried only
        # when the printed order finds nobody, and counted as its own rule.
        if not cand and ' ' not in sur:
            rule, cand = find(sur, given)
            if rule:
                rule += ', roster printed surname first'
        if not cand:
            stats['unmatched'] += 1
            continue
        if len(cand) > 1:
            stats['ambiguous (refused)'] += 1
            continue
        stats['matched: ' + rule] += 1
        found[key] = cand[0]
    # One wage row claimed by two roster names is refused for both.
    claims = collections.Counter(found.values())
    for k in [k for k, i in found.items() if claims[i] > 1]:
        del found[k]
        stats['claimed twice (refused)'] += 1
    stats['roster teachers'] = len(teachers)
    stats['matched'] = len(found)
    return found, teachers, stats


# ===================================================================== the aggregates
MIN_CELL = 3            # no statistic or band is published resting on fewer people
PART_YEAR = 0.5         # OUR RULE: gross below half the year's matched median is part-year
BAND = 10000
BAND_LO, BAND_HI = 40000, 120000   # open-ended bands below and above, so the tails merge
LONGEVITY_MAX = 5700    # the 2024-2027 agreement, Article XVI F: up to $5,700 on step 13
TOP_STEP = 13
FIELDS = ['fy', 'measure', 'value', 'unit', 'note']


def schedule():
    """{lane: {step: (fy25, fy26)}} from the agreement's schedule, as read into the CSV."""
    out = collections.defaultdict(dict)
    for r in csv.DictReader(open(SCHEDULE, encoding='utf-8')):
        out[r['lane']][int(r['step'])] = (int(r['fy25']), int(r['fy26']))
    return out


def calendar_cell(fy25, fy26):
    """OUR approximation of a full calendar year 2025 on one cell: half of each contract
    year's rate (January-June at FY2025's, July-December at FY2026's)."""
    return round((fy25 + fy26) / 2.0)


def pct(xs, q):
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def aggregates():
    out = []

    def put(fy, measure, value, unit, note=''):
        out.append({'fy': fy, 'measure': measure,
                    'value': ('%.2f' % value if isinstance(value, float) else value),
                    'unit': unit, 'note': note})
    sched = schedule()
    lanes = sorted(sched, key=lambda l: sched[l][TOP_STEP][0])
    for fy in sorted(PAGES):
        rows, st = wage_list(fy)
        meta = list(csv.DictReader(open(os.path.join(PRIV, 'pages', str(fy), 'pages.tsv')),
                                   delimiter='\t'))
        kinds = collections.Counter(m['kind'] for m in meta)
        put(fy, 'wage_pages', len(meta), 'pages', '; '.join('%d %s' % (v, k) for k, v in
                                                              sorted(kinds.items())))
        heads = collections.Counter()
        for pg in PAGES[fy][1]:
            for o in _obs(os.path.join(PRIV, 'pages', str(fy), 'p%d.upright.png.fast.tsv' % pg)):
                if re.search(r'wages|compensation', o['t'], re.I):
                    heads[' '.join(o['t'].split()).upper()] += 1
        # The heading as printed: the period the list covers is CALENDAR wherever it says.
        # Where no heading is printed the list is taken to be the calendar year the report
        # is named for, like its neighbours -- OUR assumption, and this row says which.
        put(fy, 'list_heading', heads.most_common(1)[0][0] if heads else 'none printed',
            'text', 'the wage pages\' own heading, as read' if heads else
            'no heading on the wage pages; calendar %d assumed from the years that print one'
            % fy)
        put(fy, 'wage_rows', st['rows'], 'people',
            'name and amount in one printed row; calendar %d' % fy)
        put(fy, 'wage_rows_refused', st['refused'], 'rows',
            'a name with no amount, or an amount with no name')
        put(fy, 'wage_rows_printed_twice', st['printed twice, dropped'], 'rows',
            'identical name and amount printed on two pages by the town')
        put(fy, 'wage_total', round(st['total'], 2), 'dollars',
            'sum of every row read; the list prints no total to check it against')
        if st['tl_amounts']:
            put(fy, 'textlayer_amounts', st['tl_amounts'], 'amounts',
                'amounts the PDF\'s own text layer carries on the wage pages')
            put(fy, 'textlayer_agree', st['tl_agree'], 'amounts',
                'of those, read identically by us, as a multiset')
        put(fy, 'amounts_both_readings_agree', st['check_both_readings_agree'], 'rows',
            'Vision\'s fast and accurate readings gave the same amount')
        put(fy, 'amounts_fast_only', st['check_fast_only'] + st['check_disagree'], 'rows',
            'read by one Vision level only, or the two disagreed')
        found, teachers, ms = match(fy, rows)
        put(fy, 'roster_teachers', ms['roster teachers'], 'people',
            'distinct names on the printed school rosters under a teaching title')
        put(fy, 'roster_teachers_our_rule', ms['roster unclassified line under a teaching '
                                               'heading (our rule)'], 'people',
            'of those, lines with no title printed under a grade or subject heading')
        put(fy, 'matched', len(found), 'people', 'roster teacher with exactly one wage row')
        put(fy, 'match_rate', round(100.0 * len(found) / ms['roster teachers'], 1), 'percent')
        for k in sorted(ms):
            if k.startswith('matched: '):
                put(fy, 'matched_by_rule', ms[k], 'people', k[len('matched: '):])
        put(fy, 'unmatched', ms['unmatched'], 'people', 'no wage row under any rule')
        put(fy, 'refused_ambiguous', ms['ambiguous (refused)'] + ms['claimed twice (refused)'],
            'people', 'two candidate wage rows, or one wage row claimed by two roster names')
        if fy <= LAST_DEPT_YEAR:
            sch = sum(1 for i in found.values() if 'SCHOOL' in rows[i]['dept'].upper())
            put(fy, 'matched_tagged_school', sch, 'people',
                'matched rows the town\'s own list tags SCHOOL (it prints a department '
                'through calendar 2017)')
        pay = [rows[i]['amt'] for i in found.values()]
        med_all = statistics.median(pay)
        cut = PART_YEAR * med_all
        full = sorted(a for a in pay if a >= cut)
        put(fy, 'part_year', len(pay) - len(full), 'people',
            'gross below half the matched median (%s), our rule' % ('$%s' % format(round(cut), ',')))
        put(fy, 'full_year', len(full), 'people', 'matched, at or above that line')
        if len(full) < MIN_CELL:
            continue
        put(fy, 'median', round(statistics.median(full), 2), 'dollars',
            'gross pay, full-year matched teachers')
        put(fy, 'p25', round(pct(full, 0.25), 2), 'dollars', 'lower quartile')
        put(fy, 'p75', round(pct(full, 0.75), 2), 'dollars', 'upper quartile')
        bands = [(None, BAND_LO)] + [(a, a + BAND) for a in range(BAND_LO, BAND_HI, BAND)] + \
            [(BAND_HI, None)]
        counts = [sum(1 for a in full if (lo is None or a >= lo) and (hi is None or a < hi))
                  for lo, hi in bands]
        # Empty tails go; then a thin tail merges inward until it holds MIN_CELL people, so
        # no band is one person.
        while counts and counts[0] == 0:
            del bands[0], counts[0]
        while counts and counts[-1] == 0:
            del bands[-1], counts[-1]
        bands[0] = (None, bands[0][1])
        bands[-1] = (bands[-1][0], None)
        while len(bands) > 2 and 0 < counts[0] < MIN_CELL:
            bands[1] = (None, bands[1][1])
            counts[1] += counts[0]
            del bands[0], counts[0]
        while len(bands) > 2 and 0 < counts[-1] < MIN_CELL:
            bands[-2] = (bands[-2][0], None)
            counts[-2] += counts[-1]
            del bands[-1], counts[-1]
        for (lo, hi), c in zip(bands, counts):
            put(fy, 'band', c, 'people', '%s-%s' % ('' if lo is None else lo,
                                                     '' if hi is None else hi))
        if fy == 2025:
            s1 = calendar_cell(*sched['Bach'][1])
            put(fy, 'below_step1_bach', sum(1 for a in full if a < s1), 'people',
                'full-year matched teachers paid below the calendar-2025 step 1 bachelor\'s '
                'cell ($%s)' % format(s1, ','))
            put(fy, 'step1_bach_calendar', s1, 'dollars',
                'half the FY2025 cell plus half the FY2026 cell, our approximation')
            for lane in lanes:
                top = calendar_cell(*sched[lane][TOP_STEP])
                put(fy, 'top_step_calendar', top, 'dollars', lane)
                put(fy, 'at_or_above_top', sum(1 for a in full if a >= top), 'people', lane)
                put(fy, 'above_top_plus_longevity',
                    sum(1 for a in full if a >= top + LONGEVITY_MAX), 'people', lane)
    return out


def render(rows):
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def write_private(fy, rows, found, teachers):
    """The name-level reading and match -- PRIVATE, gitignored, never published."""
    d = os.path.join(PRIV, 'out')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'wages-%d.csv' % fy), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['fy', 'page', 'name', 'department', 'amount', 'check'])
        for r in rows:
            w.writerow([fy, r['page'], ' '.join(r['parts']), r['dept'], '%.2f' % r['amt'],
                        r['check']])
    with open(os.path.join(d, 'match-%d.csv' % fy), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['fy', 'roster_name', 'how', 'wage_name', 'amount'])
        for key, (g, s, how) in sorted(teachers.items()):
            i = found.get(key)
            w.writerow([fy, '%s %s' % (g, s), how,
                        ' '.join(rows[i]['parts']) if i is not None else '',
                        '%.2f' % rows[i]['amt'] if i is not None else ''])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--ocr', action='store_true', help='re-read every wage page first')
    a = ap.parse_args()
    if a.ocr:
        for fy in sorted(PAGES):
            ocr_year(fy)
    if not os.path.isdir(os.path.join(PRIV, 'pages')):
        fail('the private reading is not on this machine (build/private/teacher-pay/, '
             'gitignored by design -- rule 13e). Run with --ocr; it needs the annual-report '
             'PDFs (scripts/sync_archive.py --pull) and swift.')
    text = render(aggregates())
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        if cur != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('teacher pay distribution: current (%d rows)' % (text.count('\n') - 1))
        return 0
    for fy in sorted(PAGES):
        rows, _ = wage_list(fy)
        found, teachers, _ = match(fy, rows)
        write_private(fy, rows, found, teachers)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
