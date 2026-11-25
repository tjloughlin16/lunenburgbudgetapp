#!/usr/bin/env python3
"""THE OFFICIAL FY2026 SCHOOL BUDGET, line by line, read off the documents the School Committee
approved on 12 March 2025 -- and the two reconciliations that rest on it.

    python3.11 scripts/extract_fy26_approved_budget.py           # write the CSV and the finding
    python3.11 scripts/extract_fy26_approved_budget.py --check   # fail if either would change

    sources/data/fy26-approved-budget-lines.csv    every line of the chosen document, with its page and y
    notes/findings/FY26-BUDGET-THREE-WAYS.md        the copies compared; official vs MUNIS; FY27 docs' FY26 vs official

TJ, 25 November 2026: "why are we using a workbook built in FY27 ... we need to use the OFFICIAL FY26
budget docs", and "THEN we could do a reconciliation AGAIN if they give FY26 in the FY27 docs and
they disagree there".

HOW IT READS A PAGE (rule 13b). Every copy is a digital PDF with a text layer. Words are grouped into
printed lines by their y, and a figure is placed in a column by the CENTRE of its x, inside a band
measured off that document's own header -- never by its order on the line, because a line with no
FY25 figure would otherwise put its FY26 figure under FY25. The bands are in DOCS and were measured
by hand from the header words; a copy whose lines then fail to sum to its own printed totals is
refused, which is what makes a wrong band safe.

WHAT TIES (the document's own identities, never ours):
  - every copy: lines sum to its printed TOTAL EXPENSES, TOTAL SALARIES and TOTAL BUDGET;
  - the copies that print a "<code> - <name> Total" row: each group's lines sum to it.
A copy that does not tie writes nothing.

WHAT THIS DOES NOT ESTABLISH. These are the documents of 12 March 2025. MUNIS opened FY2026 with
$500,000 more than any of them prints, and no document of that date or earlier says how that
$500,000 was spread across lines; so the comparison against MUNIS separates what the March budget
explains from what it cannot, and does not say which lines the $500,000 went to.
"""
import argparse
import collections
import csv
import difflib
import io
import os
import re
import sys

import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from check_function_crosswalk import school_ledger  # noqa: E402

DATA = os.path.join(ROOT, 'sources', 'data')
OUT_CSV = os.path.join(DATA, 'fy26-approved-budget-lines.csv')
OUT_MD = os.path.join(ROOT, 'notes', 'findings', 'FY26-BUDGET-THREE-WAYS.md')
DB = 'sources/district-budget/docs/'

# key: (archive path, publisher's title, label edge, FY26 band (centre x), what the FY26 column is headed)
DOCS = collections.OrderedDict([
    ('approved', (DB + 'fy26-school-dept-approved-budget-3-12-25.pdf',
                  'FY26 School Dept. Approved Budget 3-12-25', 330, (410, 490), 'FY26 Budgeted')),
    ('tm-target', (DB + 'final-fy26-town-manager-39-s-target-budget-approved-3-12-25.pdf',
                   "FINAL FY26 Town Manager's Target Budget Approved 3-12-25", 690, (895, 1000),
                   'FY26 Budgeted')),
    ('tm-target-packet', (DB + 'sc-meetings/2025-03-12-final-fy26-town-manager-s-target-budget-'
                          'approved-3-12-25.pdf',
                          "FINAL FY26 Town Manager's Target Budget Approved 3-12-25 (12 March 2025 "
                          'meeting packet)', 440, (575, 642), 'FY26 Budgeted')),
    ('sc-approved-level', (DB + 'final-fy26-sc-approved-budget-3-12-25-with-level-service-budget.pdf',
                           'Final FY26 SC Approved Budget 3-12-25 with Level Service Budget', 740,
                           (950, 1066), 'FY26 Budgeted')),
    ('tm-budget-3-12', (DB + '3-12-25-town-manager-39-s-budget.pdf',
                        "3/12/25 Town Manager's Budget", 290, (540, 600), 'FY26 TM 031225')),
])
CHOSEN = 'tm-target'
# Copies printed in whole dollars, rounded from the cents the others print. Their lines do not
# sum exactly to their own printed totals (see tie()), so they are never the extract: an exact
# tie exists in the cents copies and wins (notes/process/TOLERANCES.md).
WHOLE_DOLLARS = ('approved', 'tm-budget-3-12')
EXPECTED_TOTAL = 25787474.00
FOOTNOTE_DIFF = 1.19          # the footnote's 'rounding error of 1.19', asserted against the page   # printed TOTAL BUDGET on every copy; asserted, never used as a value

GROUP = re.compile(r'^(\d{4})\s*-\s*(.+?)\s*$')
GROUP_TOTAL = re.compile(r'^(\d{4})\s*-\s*(.+?)\s+Total\s*$', re.I)
TOTALS = {'TOTAL EXPENSES:': 'expenses', 'TOTAL SALARIES:': 'salaries', 'TOTAL BUDGET:': 'budget'}


def fail(msg):
    raise SystemExit('extract_fy26_approved_budget: ' + msg)


def num(s, packet=False):
    """A printed figure, or None where the column is empty. '-' and '$ -' print zero."""
    s = s.strip()
    if packet:   # the packet copy wraps every cell in '($ ... )' as decoration, not as a sign
        s = re.sub(r'^\(\$', '', s)
        if s.endswith(')') and s.count(')') > s.count('('):
            s = s[:-1]
    s = s.replace('$', '').replace(',', '').strip()
    if s == '':
        return None
    if s in ('-', '-)'):
        return 0.0
    neg = s.startswith('(') and s.endswith(')')
    s = s.strip('()')
    if s.startswith('-'):
        neg, s = True, s[1:]
    try:
        v = float(s)
    except ValueError:
        return 'BAD'
    return -v if neg else v


def rows_of(key):
    path, _, lmax, (lo, hi), _ = DOCS[key]
    out = []
    with pdfplumber.open(os.path.join(ROOT, path)) as pdf:
        for pn, pg in enumerate(pdf.pages, 1):
            lines = {}
            for w in pg.extract_words():
                t = w['top']
                k = next((kk for kk in lines if abs(kk - t) <= 2.5), t)
                lines.setdefault(k, []).append(w)
            for t in sorted(lines):
                ws = sorted(lines[t], key=lambda w: w['x0'])
                mid = lambda w: (w['x0'] + w['x1']) / 2  # noqa: E731
                label = ' '.join(w['text'] for w in ws
                                 if mid(w) <= lmax and w['text'] not in ('$', '($'))
                band = ''.join(w['text'] for w in ws if lo < mid(w) <= hi)
                out.append(dict(page=pn, y=round(t, 1), label=re.sub(r'\s+-$', '', re.sub(r'\s+', ' ', label).strip()),
                                raw=band, value=num(band, packet=(key == 'tm-target-packet'))))
    return out


def structure(key):
    """Walk the printed lines into sections, code groups, lines and printed totals."""
    section, group, prev = None, None, None
    lines, gtotals, totals, foot = [], [], {}, []
    for r in rows_of(key):
        lab, v = r['label'], r['value']
        if lab.upper().startswith('DESCRIPTION,'):
            new = lab.split(',', 1)[1].strip().lower()
            # Sections run expenses then salaries, once. The packet copy repeats
            # 'DESCRIPTION, EXPENSES' as a running header on every page; a header that would
            # step backwards, or repeats the section already open, is that running header.
            if new != section and not (section == 'salaries' and new == 'expenses'):
                section, group = new, None
        elif lab in TOTALS:
            totals[TOTALS[lab]] = v
        elif GROUP_TOTAL.match(lab):
            g = GROUP_TOTAL.match(lab)
            gtotals.append(dict(section=section, code=g.group(1), name=g.group(2), value=v, page=r['page'],
                                y=r['y']))
        elif GROUP.match(lab) and v is None:
            g = GROUP.match(lab)
            group = (g.group(1), g.group(2))
        elif section and lab:
            if v == 'BAD':
                fail('%s p%d y%s: cannot read %r on %r' % (key, r['page'], r['y'], r['raw'], lab))
            # A line set apart by a blank printed row is outside the group above it (the salary
            # reserve). Measured on the page, not named.
            if prev and prev['page'] == r['page'] and r['y'] - prev['y'] > 1.6 * PITCH[key]:
                group = None
            lines.append(dict(section=section, code=group[0] if group else '',
                              group=group[1] if group else '', line=lab, fy26=v,
                              page=r['page'], y=r['y']))
        elif v not in (None, 'BAD') and not lab and 'budget' in totals:
            # Under the totals the cents copy prints what its columns actually sum to, beneath
            # '* Difference between summation of all columns and total budget number introduces
            # a rounding error of 1.19.' -- in the order expenses, salaries, budget.
            foot.append(v)
        elif v not in (None, 'BAD') and section:
            fail('%s p%d y%s: a figure %r with no label' % (key, r['page'], r['y'], r['raw']))
        if section and lab:
            prev = r
    if foot and len(foot) != 3:
        fail('%s: %d figures under the totals, expected the three column sums' % (key, len(foot)))
    return dict(lines=lines, gtotals=gtotals, totals=totals,
                foot=dict(zip(('expenses', 'salaries', 'budget'), foot)) if foot else {})


def pitch(key):
    ys = collections.defaultdict(list)
    for r in rows_of(key):
        ys[r['page']].append(r['y'])
    gaps = sorted(b - a for p in ys for a, b in zip(ys[p], ys[p][1:]) if b > a)
    return gaps[len(gaps) // 2]


PITCH = {}


def tie(key, doc):
    """The document's own identities. Returns the list of checks that closed, or fails."""
    L, T = doc['lines'], doc['totals']
    s = lambda xs: round(sum(x['fy26'] or 0 for x in xs), 2)  # noqa: E731
    got = dict(expenses=s([x for x in L if x['section'] == 'expenses']),
               salaries=s([x for x in L if x['section'] == 'salaries']), budget=s(L))
    # The printed TOTALs are ROUNDED in every copy. The cents copies that print a footnote
    # state what the columns really sum to; those must tie to the cent, and the printed total
    # must sit within the footnote's own stated difference of it. A copy with no footnote
    # cannot tie exactly to anything it prints: its misses are RECORDED and printed, never
    # closed, and it is checked line by line against the extract instead.
    doc['misses'] = []
    F = doc['foot']
    for k in ('expenses', 'salaries', 'budget'):
        if T.get(k) is None:
            fail('%s: no printed TOTAL %s found' % (key, k.upper()))
        if F:
            # The workbook behind this copy holds cells to more places than a cent (B332 'E.S.
            # Administrative Secretary', E332 = 60783.3504 in the FinCom .xlsx), the PDF prints
            # each to the cent, and the footnote sums the unprinted values. So the printed lines
            # can miss the footnote by at most half a cent each: that bound is derived, not tuned.
            n = len([x for x in L if x['section'] == k] if k != 'budget' else L)
            if abs(got[k] - F[k]) > 0.005 * n:
                fail('%s: lines sum to %s against the column sum it prints, %s' % (key, got[k], F[k]))
            if abs(got[k] - F[k]) > 0.005:
                doc.setdefault('subcent', []).append((k, got[k], F[k]))
        if abs(got[k] - T[k]) > 0.005:
            doc['misses'].append((k, got[k], T[k]))
    if F and abs((F['budget'] - T['budget']) - FOOTNOTE_DIFF) > 0.005:
        fail('%s: the footnote says the columns exceed TOTAL BUDGET by %s; they exceed it by %s'
             % (key, FOOTNOTE_DIFF, round(F['budget'] - T['budget'], 2)))
    if key == CHOSEN and not F:
        fail('the extract must be a copy that prints its own column sums')
    if abs(T['budget'] - EXPECTED_TOTAL) > 0.005:
        fail('%s prints TOTAL BUDGET %s, not %s' % (key, T['budget'], EXPECTED_TOTAL))
    # Group totals: lines between the group header and its Total row.
    n = 0
    for gt in doc['gtotals']:
        members = [x for x in L if x['section'] == gt['section'] and x['code'] == gt['code']
                   and x['group'].lower() == gt['name'].lower()]
        if not members:
            members = [x for x in L if x['section'] == gt['section'] and x['code'] == gt['code']
                       and gt['name'].lower().startswith(x['group'].lower()[:12])]
        if abs(s(members) - (gt['value'] or 0)) > 0.005:
            # A subtotal that does not foot is a fact about THAT copy, recorded and printed.
            # The extract may have none.
            if key == CHOSEN:
                fail('%s: group %s %s lines sum to %s against its printed Total %s'
                     % (key, gt['code'], gt['name'], s(members), gt['value']))
            doc.setdefault('gmiss', []).append(dict(gt, lines=s(members)))
            continue
        n += 1
    return n


SCHOOLS = (('primaryschool', 'ps'), ('elementaryschool', 'es'), ('middleschool', 'ms'),
           ('highschool', 'hs'))


def norm(t):
    """A label reduced to letters and digits, with the four schools' long names shortened to the
    abbreviation the documents use elsewhere ('High School Psychologist' / 'H.S. Psychologist')."""
    t = re.sub(r'[^a-z0-9]', '', t.lower())
    for long_, short in SCHOOLS:
        t = t.replace(long_, short)
    return t


def align(a, b):
    """Pair two line lists. Returns [(a_line|None, b_line|None, how)].

    By label, never by amount: amount is what is being compared. In three passes, each taking
    only what the one before left: the same section, code and label; the same section and
    label under ANOTHER code (how='code'); then a label that differs only in spelling within
    the same section and code (how='spelling', difflib ratio >= 0.8, or one label the other with
    words added: 'P.S. Science Supplies (includes STEM)'). Duplicate labels pair
    in printed order.
    """
    out, ra, rb = [], list(a), list(b)

    def take(keyf, how, test=None):
        nonlocal ra, rb
        left = []
        for x in ra:
            j = next((i for i, y in enumerate(rb)
                      if (keyf(x) == keyf(y) if test is None else test(x, y))), None)
            if j is None:
                left.append(x)
            else:
                out.append((x, rb.pop(j), how))
        ra = left
    # First as printed (case and spacing aside), because two labels can differ only by a full
    # stop and still be two lines: 'Kind Long Term Substitutes' and 'Kind. Long Term Substitutes'.
    take(lambda x: (x['section'], x['code'], ' '.join(x['line'].lower().split())), 'same')
    take(lambda x: (x['section'], x['code'], norm(x['line'])), 'same')
    take(lambda x: (x['section'], norm(x['line'])), 'code')
    # Spelling: the closest pairs first, so 'Spcl Ed Generl' meets 'Spcl Ed General' before
    # 'ACE General' can claim it.
    cand = sorted(((difflib.SequenceMatcher(a=norm(x['line']), b=norm(y['line'])).ratio(), i, j)
                   for i, x in enumerate(ra) for j, y in enumerate(rb)
                   if x['section'] == y['section'] and x['code'] == y['code']), reverse=True)
    ua, ub = set(), set()
    for r, i, j in cand:
        na, nb = norm(ra[i]['line']), norm(rb[j]['line'])
        if (r >= 0.8 or na.startswith(nb) or nb.startswith(na)) and i not in ua and j not in ub:
            out.append((ra[i], rb[j], 'spelling'))
            ua.add(i)
            ub.add(j)
    ra = [x for i, x in enumerate(ra) if i not in ua]
    rb = [y for j, y in enumerate(rb) if j not in ub]
    out += [(x, None, 'only-a') for x in ra] + [(None, y, 'only-b') for y in rb]
    return out


def money(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def usd(v, cents=False):
    if v is None:
        return 'blank'
    s = '{:,.2f}'.format(abs(v)) if cents or abs(v - round(v)) > 0.004 else '{:,.0f}'.format(abs(v))
    return ('-$' if v < 0 else '$') + s


def march_lines(path=OUT_CSV):
    """The extract, as the dicts against_munis() takes: section, code, group, line, fy26."""
    return [dict(section=r['section'], code=r['code'], group=r['group'], line=r['line'],
                 fy26=None if r['fy26_approved'] == '' else float(r['fy26_approved']))
            for r in csv.DictReader(open(path, encoding='utf-8'))]


def against_munis(off, led):
    """The March lines against the MUNIS accounts, one rule, used by the finding AND the page.

    In order, each step taking only what the last left:
      landed    same code, an account of the same amount within a dollar (the March copy prints
                cents, MUNIS prints whole dollars on its budget columns);
      moved     an unclaimed account of the same amount under ANOTHER code;
      joined    two or three March lines in one code summing, within a dollar, to one unclaimed
                account in that code;
      unlanded / spare   what is left on each side: amounts that changed between the two.
    Amount is not a key: a match shows a figure of that size on both sides, never that the two
    are the same line, and equal amounts pair arbitrarily (largest first, then printed order).
    """
    import itertools
    pool = collections.defaultdict(list)
    for a in led:
        if abs(money(a['original'])) >= 0.5:
            pool[a['function']].append(a)
    landed, unlanded = [], []
    for x in sorted([x for x in off if abs(x['fy26'] or 0) >= 0.5], key=lambda x: -(x['fy26'] or 0)):
        cand = pool.get(x['code'], [])
        j = next((i for i, a in enumerate(cand) if abs(money(a['original']) - x['fy26']) <= 1.0), None)
        if j is None:
            unlanded.append(x)
        else:
            landed.append((x, cand.pop(j)))
    spare = [a for c in pool for a in pool[c]]
    moved = []
    for x in list(unlanded):
        j = next((i for i, a in enumerate(spare) if abs(money(a['original']) - x['fy26']) <= 1.0), None)
        if j is not None:
            moved.append((x, spare.pop(j)))
            unlanded.remove(x)
    joined = []
    for c in sorted({a['function'] for a in spare}):
        ls = [x for x in unlanded if x['code'] == c]
        for a in [a for a in spare if a['function'] == c]:
            hit = next((combo for n in (2, 3) for combo in itertools.combinations(ls, n)
                        if abs(sum(x['fy26'] for x in combo) - money(a['original'])) <= 1.0), None)
            if hit:
                joined.append((list(hit), a))
                ls = [x for x in ls if x not in hit]
    for hit, a in joined:
        spare.remove(a)
        for x in hit:
            unlanded.remove(x)
    return dict(landed=landed, moved=moved, joined=joined, unlanded=unlanded, spare=spare)


def build():
    docs = {}
    for k in DOCS:
        PITCH[k] = pitch(k)
        d = structure(k)
        d['n_group_totals'] = tie(k, d)
        docs[k] = d
    off = docs[CHOSEN]['lines']

    # --- the copies against the chosen one -------------------------------------------------
    copies = []
    for k in DOCS:
        if k == CHOSEN:
            continue
        pairs = align(off, docs[k]['lines'])
        v = lambda x: (x or {}).get('fy26') or 0  # noqa: E731
        # A whole-dollar copy agrees with a line when it prints that line rounded to the dollar.
        tol = 0.5 + 0.005 if k in WHOLE_DOLLARS else 0.005
        diff = [p for p in pairs if abs(v(p[0]) - v(p[1])) > tol]
        unpaired = [p for p in pairs if p[2] in ('only-a', 'only-b') and abs(v(p[0]) - v(p[1])) <= tol]
        copies.append(dict(key=k, n=len(docs[k]['lines']), pairs=pairs, diff=diff, unpaired=unpaired,
                           rounded=sum(1 for a, b, h in pairs if a and b and 0.005 < abs(v(a) - v(b)) <= tol),
                           how=collections.Counter(h for _, _, h in pairs)))

    # --- official against MUNIS ---------------------------------------------------------------
    led = school_ledger()
    munis_total = round(sum(money(a['original']) for a in led), 2)
    by_code_off = collections.defaultdict(float)
    for x in off:
        by_code_off[x['code']] += x['fy26'] or 0
    by_code_led = collections.defaultdict(float)
    for a in led:
        by_code_led[a['function']] += money(a['original'])
    codes = sorted(set(by_code_off) | set(by_code_led), key=lambda c: (c == '', c))
    code_rows = [dict(code=c, official=round(by_code_off.get(c, 0), 2), munis=round(by_code_led.get(c, 0), 2))
                 for c in codes]
    for r in code_rows:
        r['diff'] = round(r['munis'] - r['official'], 2)

    M = against_munis(off, led)
    landed, moved, joined, unlanded, spare = (M['landed'], M['moved'], M['joined'], M['unlanded'],
                                              M['spare'])

    # --- the FY27 documents' FY26 column against the official ----------------------------------
    book = [r for r in csv.DictReader(open(os.path.join(DATA, 'lps-budget-lines.csv')))
            if r['kind'] == 'line']
    b27 = []
    for r in book:
        li = (r['line_item'] or '').strip()
        sec = (r['section'] or '').strip().lower()
        if sec not in ('expenses', 'salaries') or not li or li.upper().startswith('DESCRIPTION,') \
                or GROUP.match(li) and r['fy26_final'] in ('', None) \
                or li.upper().startswith('TOTAL') or GROUP_TOTAL.match(li):
            continue
        g = GROUP.match(r['function_group'] or '')
        v = None if r['fy26_final'] in ('', None) else float(r['fy26_final'])
        b27.append(dict(section=sec, code=g.group(1) if g else '', group=g.group(2) if g else '',
                        line=li, fy26=v, row=r['row']))
    total27 = round(sum(x['fy26'] or 0 for x in b27), 2)
    pairs27 = align(off, b27)
    v = lambda x: (x or {}).get('fy26') or 0  # noqa: E731
    # The FY27 workbook prints whole dollars: a line agrees when it is the official line rounded.
    d27 = [p for p in pairs27 if abs(v(p[0]) - v(p[1])) > 0.505]
    recoded27 = [p for p in pairs27 if p[2] == 'code']

    # THE THREE WAYS, line by line. March to the FY27 workbook by LABEL (align); the workbook
    # line to a MUNIS account by AMOUNT under its own code, within a dollar. The second link is
    # not a key: it shows an account of that size exists under that code, never that it is the line.
    pool27 = collections.defaultdict(list)
    for a in led:
        pool27[a['function']].append(a)
    three = []
    for a, b, how in sorted(pairs27, key=lambda p: (p[0] or p[1])['section'] + str(
            ((p[0] or p[1]).get('page'), (p[0] or p[1]).get('y'), (p[0] or p[1]).get('row')))):
        acct = None
        if b and b['fy26'] and abs(b['fy26']) >= 0.5:
            cand = pool27.get(b['code'], [])
            j = next((i for i, x in enumerate(cand) if abs(money(x['original']) - b['fy26']) <= 1.0), None)
            if j is not None:
                acct = cand.pop(j)
        three.append(dict(off=a, b27=b, how=how, acct=acct))

    return dict(docs=docs, off=off, copies=copies, led=led, munis_total=munis_total, code_rows=code_rows,
                landed=landed, moved=moved, unlanded=unlanded, spare=spare, joined=joined, b27=b27,
                total27=total27, pairs27=pairs27, d27=d27, recoded27=recoded27, three=three)


def csv_text(R):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['seq', 'section', 'code', 'group', 'line', 'fy26_approved', 'page', 'y', 'document', 'sha256'])
    path = DOCS[CHOSEN][0]
    sha = sha256(path)
    for i, x in enumerate(R['off'], 1):
        w.writerow([i, x['section'], x['code'], x['group'], x['line'],
                    '' if x['fy26'] is None else ('%.2f' % x['fy26']), x['page'], x['y'], path, sha])
    return buf.getvalue()


def sha256(path):
    import hashlib
    return hashlib.sha256(open(os.path.join(ROOT, path), 'rb').read()).hexdigest()


def md_text(R):
    return render(R)


def render(R):
    D = R['docs']
    ch = D[CHOSEN]
    T, F = ch['totals'], ch['foot']
    v = lambda x: (x or {}).get('fy26') or 0  # noqa: E731
    gap = round(R['munis_total'] - T['budget'], 2)
    off_sum = F['budget']
    nd = len(R['d27'])
    d27_net = round(sum(v(b) - v(a) for a, b, _ in R['d27']), 2)
    differs = [t for t in R['three'] if abs(v(t['off']) - v(t['b27'])) > 0.505
               or (t['acct'] is None and abs(v(t['b27'])) >= 0.5)]
    up = sorted([t for t in R['d27'] if v(t[1]) > v(t[0])], key=lambda t: v(t[0]) - v(t[1]))
    down = [t for t in R['d27'] if v(t[1]) < v(t[0])]
    cancel, used = [], set()
    for i, (a, b, _) in enumerate(R['d27']):
        for j, (c, d, _) in enumerate(R['d27']):
            if j > i and i not in used and j not in used and abs((v(b) - v(a)) + (v(d) - v(c))) < 0.505:
                cancel.append((R['d27'][i], R['d27'][j]))
                used |= {i, j}
    sal_versions = {}
    for k in DOCS:
        sig = tuple(v(x) for x in D[k]['lines'] if x['section'] == 'salaries'
                    and norm(x['line']) in ('msadminstrativesecretary', 'hsadministrativesecretary',
                                            'hsguidancesecretary'))
        sal_versions.setdefault(tuple(round(z) for z in sig), []).append(k)
    out = []
    w = out.append
    w('<!-- GENERATED by scripts/extract_fy26_approved_budget.py -- do not edit; re-run it. -->')
    w('# The FY2026 school budget, three ways')
    w('')
    w('The budget the School Committee approved on 12 March 2025, the budget MUNIS opened FY2026 with, '
      'and the FY2026 column of the district\'s FY2027 workbook, compared line by line.')
    w('')
    w('## What it shows')
    w('')
    w('- **MUNIS opened FY2026 %s above the approved budget.** The 12 March 2025 documents print TOTAL '
      'BUDGET %s; the Town\'s period 12 report holds an original appropriation of %s across %d accounts.'
      % (usd(gap), usd(T['budget']), usd(R['munis_total']), len(R['led'])))
    n27 = [t for t in R['three'] if abs(v(t['b27'])) >= 0.5]
    w('- **The FY2027 workbook\'s FY2026 column follows MUNIS, not March.** %d of its %d lines with money '
      'have a MUNIS account at the same amount under the same code. It sums to %s and differs from March on '
      '%d lines, netting %s.' % (len([t for t in n27 if t['acct']]), len(n27), usd(R['total27']), nd,
                                 usd(d27_net)))
    w('- **%d of the March budget\'s %d lines with money land in MUNIS** at the same amount under the same '
      'code; %d more land under another code, and %d groups of lines went into one account.'
      % (len(R['landed']), len([x for x in R['off'] if abs(v(x)) >= 0.5]), len(R['moved']), len(R['joined'])))
    w('- **Five copies of the March budget print the same total and %d different salary pages.** The '
      'extract is the one whose lines tie to the column sums it prints.' % len(sal_versions))
    w('')
    w('What it does not show: which of the changes between March and MUNIS are the $500,000 and which '
      'are money moved between lines. Both look the same here. See *What this does not establish*.')
    w('')

    # ---- the lines that moved ------------------------------------------------------------
    w('## Where March and the FY2027 workbook\'s FY2026 column differ')
    w('')
    w('Every line whose FY2026 figure differs by more than rounding, with the MUNIS account of the '
      'workbook\'s amount under the workbook\'s code where one exists. Raised lines first.')
    w('')
    w('| code | line (March) | March 2025 | FY27 workbook, FY26 | change | MUNIS account at that amount |')
    w('|---|---|---:|---:|---:|---|')
    acct_of = {id(t['b27']): t['acct'] for t in R['three'] if t['b27']}
    for a, b, how in up + down:
        acc = acct_of.get(id(b)) if b else None
        lab = (a or b)['line']
        if a and b and norm(a['line']) != norm(b['line']):
            lab += ' (workbook: %s)' % b['line']
        if not a:
            lab = '*not in March:* ' + b['line']
        if not b:
            lab += ' *(not in the workbook)*'
        w('| %s | %s | %s | %s | %s | %s |' % (
            (a or b)['code'] or 'none', lab, usd(a['fy26'], True) if a else '--',
            usd(b['fy26']) if b else '--', usd(v(b) - v(a)),
            '`%s` %s' % (acc['account'], acc['name'].strip()) if acc else ('--' if not b or not v(b) else 'none')))
    w('| | **net** | | | **%s** | |' % usd(d27_net))
    w('')
    w('The net is %s, against the %s gap between the printed totals; the rest is the March copy\'s '
      'cents against the workbook\'s whole dollars.' % (usd(d27_net), usd(gap)))
    w('')
    if R['recoded27']:
        w('Same line, another code in the workbook: ' + '; '.join(
            '%s, %s in March, %s in the workbook' % (a['line'], a['code'], b['code']) for a, b, _ in R['recoded27']) + '.')
        w('')

    # ---- March against MUNIS ----------------------------------------------------------------
    w('## The March budget against MUNIS, code by code')
    w('')
    w('MUNIS: `%s`, FY2026 period 12, ORIGINAL APPROP, departments 300 and 301 '
      '(`check_function_crosswalk.school_ledger`). Codes where the two differ:' % R['led'][0]['doc_id'])
    w('')
    w('| code | March 2025 | MUNIS original | MUNIS minus March |')
    w('|---|---:|---:|---:|')
    for r in R['code_rows']:
        if abs(r['diff']) > 0.5:
            w('| %s | %s | %s | %s |' % (r['code'] or 'none printed', usd(r['official'], True),
                                         usd(r['munis'], True), usd(r['diff'], True)))
    w('| **all** | **%s** | **%s** | **%s** |' % (usd(off_sum, True), usd(R['munis_total'], True),
                                                   usd(round(R['munis_total'] - off_sum, 2), True)))
    w('')
    w('The March column sums the printed lines (%s), not the printed TOTAL BUDGET (%s); the document\'s '
      'own footnote gives the difference.' % (usd(off_sum, True), usd(T['budget'])))
    w('')
    w('### Lines under another code in MUNIS')
    w('')
    w('An account of the same amount, within a dollar, under a different code. Amount is not a key: this '
      'shows a figure of that size, not that it is the same line.')
    w('')
    w('| line | March code | MUNIS code | account | amount |')
    w('|---|---|---|---|---:|')
    for x, a in sorted(R['moved'], key=lambda p: -p[0]['fy26']):
        w('| %s | %s | %s | `%s` | %s |' % (x['line'], x['code'] or 'none printed', a['function'], a['account'],
                                           usd(x['fy26'], True)))
    w('')
    w('### Two or three March lines, one MUNIS account')
    w('')
    for hit, a in R['joined']:
        w('- **%s**: %s in March; MUNIS `%s` %s holds %s.' % (
            a['function'], ' + '.join('%s %s' % (x['line'], usd(x['fy26'])) for x in hit),
            a['account'], a['name'].strip(), usd(money(a['original']), True)))
    w('')
    w('### What is left on each side')
    w('')
    w('March lines with no MUNIS account of their amount anywhere, and MUNIS accounts no March line '
      'claims. These are what the table above explains line by line through the FY2027 workbook.')
    w('')
    w('| code | March lines not found | MUNIS accounts not claimed |')
    w('|---|---|---|')
    for c in sorted({x['code'] for x in R['unlanded']} | {a['function'] for a in R['spare']}):
        w('| %s | %s | %s |' % (c or 'none', '; '.join('%s %s' % (x['line'], usd(x['fy26'], True))
                                                    for x in R['unlanded'] if x['code'] == c) or '--',
                                '; '.join('`%s` %s %s' % (a['account'][-14:], a['name'].strip(),
                                                          usd(money(a['original']), True))
                                          for a in R['spare'] if a['function'] == c) or '--'))
    w('')

    # ---- the copies -------------------------------------------------------------------------
    w('## Which document is the March budget')
    w('')
    w('Five copies dated 12 March 2025 are held. All print TOTAL BUDGET %s. The extract, '
      '`sources/data/fy26-approved-budget-lines.csv`, is **%s**:' % (usd(EXPECTED_TOTAL), DOCS[CHOSEN][1]))
    w('')
    w('- it prints cents, and its %d lines sum to the column sums it prints under the totals (%s, %s, %s); '
      'its footnote says the printed TOTAL BUDGET is %s under them;' % (
          len(ch['lines']), usd(F['expenses'], True), usd(F['salaries'], True), usd(F['budget'], True),
          usd(FOOTNOTE_DIFF, True)))
    if ch.get('subcent'):
        w('- %s: the printed lines miss that sum by %s, inside half a cent a line, because the workbook behind it '
          'holds cells past the cent (FinCom `.xlsx`, E332 = 60783.3504 for E.S. Administrative Secretary);'
          % (', '.join(k for k, _, _ in ch['subcent']), ', '.join(usd(round(g - f, 2), True) for _, g, f in ch['subcent'])))
    w('- every group subtotal it prints (%d) foots to its lines;' % ch['n_group_totals'])
    w('- the School Department\'s own *%s* prints the same figure on every line, rounded to the dollar.'
      % DOCS['approved'][1])
    w('')
    w('| key | copy | archive path | lines | against the extract | printed totals vs its lines |')
    w('|---|---|---|---:|---|---|')
    w('| %s | **%s** | `%s` | %d | the extract | %s |' % (CHOSEN, DOCS[CHOSEN][1], DOCS[CHOSEN][0], len(ch['lines']),
                                                     'ties to its printed column sums'))
    for c in R['copies']:
        d = D[c['key']]
        diffs = '; '.join('%s %s, here %s' % ((a or b)['line'], usd(v(a), True), usd(v(b), True) if b and b['fy26'] is not None else 'blank')
                          for a, b, _ in c['diff']) or 'same on every line'
        if c['rounded']:
            diffs = '%d lines rounded to the dollar; %s' % (c['rounded'], diffs)
        miss = '; '.join('%s %s vs %s' % (k, usd(g, True), usd(t, True)) for k, g, t in d['misses']) or 'tie'
        for gm in d.get('gmiss', []):
            miss += '; prints %s %s Total %s, its lines sum to %s' % (gm['code'], gm['name'], usd(gm['value'], True),
                                                                     usd(gm['lines'], True))
        w('| %s | %s | `%s` | %d | %s | %s |' % (c['key'], DOCS[c['key']][1], DOCS[c['key']][0], c['n'], diffs, miss))
    w('')
    w('Three versions of the salary page, on M.S. and H.S. Administrative Secretary and H.S. Guidance '
      'Secretary: ' + '; '.join('%s in %s' % (' / '.join(usd(z) for z in sig), ', '.join(ks))
                                for sig, ks in sal_versions.items()) + '. The packet copy\'s version '
      'leaves its lines short of its own printed TOTAL SALARIES.')
    w('')

    # ---- limits -------------------------------------------------------------------------------
    w('## What this does not establish')
    w('')
    w('- **Which lines the $500,000 went to.** The workbook\'s FY2026 column is %s above March across %d '
      'lines, and %d pairs of those changes cancel to within rounding (%s). A pair like that fits money moved between '
      'lines, a recoding, or two unrelated changes of one size; nothing here tells them apart, and an '
      'addition looks the same as a reallocation. Registered in '
      '`sources/data/money-gaps.csv`; it closes with the line-item budget as voted at Town Meeting, or the '
      'district\'s own allocation of the $500,000.' % (usd(d27_net), nd, len(cancel), '; '.join(
          '%s %s and %s %s' % ((a or b)['line'], usd(v(b) - v(a)), (c or d)['line'], usd(v(d) - v(c)))
          for (a, b, _), (c, d, _) in cancel)))
    w('- **That the $500,000 is the free cash article.** The School Committee minutes of 2 April 2025 list '
      '"Article to supplement the Lunenburg schools fiscal 2026 operating budget by $500,000" '
      '(`sources/meetings/text/school-committee/2025-04-02-minutes-rr2026-11-23.txt`, line 245), and the '
      'Finance Committee of 27 January 2026 speaks of "the additional $500,000 for schools" '
      '(`sources/meetings/text/finance-committee/2026-01-27-minutes-7619.txt`, line 46). Neither gives a '
      'line. The amount matches; that it is the same money is a reading.')
    w('- **Which coding is right** where a line sits under one code in March and another in MUNIS. Nothing '
      'here settles it (see `scripts/check_function_crosswalk.py`).')
    w('- **Why the copies differ.** Three salary pages under one total is what the documents print; '
      'which was voted is not stated in any of them.')
    w('')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dump', action='store_true')
    a = ap.parse_args()
    R = build()
    if a.dump:
        for c in R['copies']:
            print(c['key'], c['n'], 'diff', len(c['diff']), 'cents', len(c['cents']), 'relabelled', c['relabelled'])
            for x, y in c['diff'][:20]:
                print('   ', x and (x['code'], x['line'], x['fy26']), '|', y and (y['code'], y['line'], y['fy26']))
        for k, d in R['docs'].items():
            print(k, len(d['lines']), 'group totals tied', d['n_group_totals'], d['totals'])
        print('munis', R['munis_total'], 'landed', len(R['landed']), 'moved', len(R['moved']),
              'unlanded', len(R['unlanded']), 'spare', len(R['spare']))
        print('fy27 col total', R['total27'], 'diffs', len(R['d27']))
        return
    files = {OUT_CSV: csv_text(R), OUT_MD: md_text(R)}
    stale = [p for p, t in files.items() if not os.path.exists(p) or open(p).read() != t]
    if a.check:
        if stale:
            fail('STALE: ' + ', '.join(os.path.relpath(p, ROOT) for p in stale))
        print('extract_fy26_approved_budget: current (%d lines, TOTAL BUDGET %s)'
              % (len(R['off']), usd(EXPECTED_TOTAL)))
        return
    for p, t in files.items():
        with open(p + '.tmp', 'w') as f:
            f.write(t)
        os.replace(p + '.tmp', p)
        print('wrote', os.path.relpath(p, ROOT))


if __name__ == '__main__':
    main()
