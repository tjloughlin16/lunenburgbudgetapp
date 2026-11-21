#!/usr/bin/env python3
"""THE SCHOOL BUDGET DRAFTS, LINE BY LINE -- every version the district prints, in one table.

    python3.11 scripts/extract_fy28_draft_lines.py            # write sources/data/budget-seasons/fy28-draft-lines.csv
    python3.11 scripts/extract_fy28_draft_lines.py --check    # ...and fail if it no longer reproduces

TJ, 20 November 2026: "we need to ingest it to put it in the DB", and "as the schools give more
line budgets, we need to process them and do the same, automatically without me asking." So
nothing here names a document. A draft is found in the district's own catalogue
(`sources/district-budget/index.csv`) by its title -- `FY28 Budget Version 1` -- and every draft
found is read, so Version 2 APPENDS rather than replaces. The key is fy + version + cost centre
+ line (+ an ordinal where the district prints one label twice under one heading).

Each draft prints, per line: FY26 Original Budget, FY26 Actual Exp, FY27 Budget, FY28 Proposed,
$ Diff, % Diff -- under cost centre headings (`1110 - School Committee`), in two sections
(expenses, then DISTRICT SALARIES), then TOTAL EXPENSES, TOTAL SALARIES, a Salary Reserve line
and TOTAL ACTUALS & BUDGET. The district prints NO subtotal per cost centre, so what can be
footed (rule 13) is:

  1. every line's own identity: FY28 Proposed - FY27 Budget = $ Diff, where a diff is printed;
  2. each section against its printed total, column by column;
  3. expenses + salaries + reserve against TOTAL ACTUALS & BUDGET.

Every check is published, one row each, in `fy28-draft-lines.footing.csv`. See `foot()` for
which misses hold a draft and which are recorded as a printed defect of a prior-year column.

A draft that fails any of them is HELD: its rows are not written, it is named in
`fy28-draft-lines.held.txt` and the script exits 2, so the refresh row names it. Never
published unfooted, never in silence. Tolerance: the $1 policy, `notes/process/TOLERANCES.md`,
labelled `within $1 rounding tolerance` and counted where it is used.

The FY26 ACTUAL column is carried because the district prints it; it may explain a line and
never feeds a headline or a projection (rule 1). Every figure is a net appropriation, not a
cost (rule 11).
"""
import argparse
import csv
import hashlib
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
OUT = os.path.join(ROOT, 'sources', 'data', 'budget-seasons', 'fy28-draft-lines.csv')
HELD = os.path.join(ROOT, 'sources', 'data', 'budget-seasons', 'fy28-draft-lines.held.txt')
FOOTING = os.path.join(ROOT, 'sources', 'data', 'budget-seasons', 'fy28-draft-lines.footing.csv')
INDEX = os.path.join(ROOT, 'sources', 'district-budget', 'index.csv')
# A draft is titled the way the district titles it: 'FY28 Budget Version 1'. Loosely, so 'FY 28
# Budget - Version 2' is found too; a memo, presentation or discussion ABOUT a version is not a
# draft. Anything this finds is either read and footed or HELD, loudly -- never skipped.
TITLE = re.compile(r'^FY\s?(\d\d)\b.*\bBudget\b.*\bVersion\s*#?\s*(\d+)\b', re.I)
NOT_A_DRAFT = re.compile(r'memo|presentation|discussion|slides|summary|letter', re.I)
TOLERANCE_PHRASE = 'within $1 rounding tolerance'
MONEY = re.compile(r'-?\$-?[\d,]+(?:\.\d+)?')
PCT = re.compile(r'-?[\d,]+(?:\.\d+)?%')
HEADING = re.compile(r'^(\d{4})\s*-\s*(.+)$')
COLS = ['fy', 'version', 'section', 'cost_centre', 'cost_centre_name', 'line', 'ordinal',
        'fy26_original', 'fy26_actual', 'fy27_budget', 'fy28_proposed', 'diff', 'pct_diff',
        'document', 'sha256', 'page']
FIG = ('fy26_original', 'fy26_actual', 'fy27_budget', 'fy28_proposed', 'diff')


def num(tok):
    t = tok.replace('$', '').replace(',', '')
    return float(t)


def drafts():
    """Every line-by-line draft the district has published, read off its catalogue."""
    out = []
    for r in csv.DictReader(open(INDEX, encoding='utf-8')):
        m = TITLE.match((r.get('label') or '').strip())
        if m and not NOT_A_DRAFT.search(r.get('label') or '') and (r.get('local') or '').lower().endswith('.pdf'):
            out.append(dict(fy=2000 + int(m.group(1)), version=int(m.group(2)), title=r['label'].strip(),
                            path=r['local'], sha256=r.get('sha256', ''), url=r.get('upstream', '')))
    return sorted(out, key=lambda d: (d['fy'], d['version']))


def pages(path):
    """Each page as its printed lines, each line as (text, [(token, right edge)]). Rule 13b: a figure
    is placed by the column it sits under, never by its order on the line -- a line with a blank
    column prints fewer figures, and taking them in order slides every one after the gap."""
    import pdf_kind
    verdict = pdf_kind.classify(os.path.join(ROOT, path))['verdict']      # rule 13d: the pages say, not a character count
    if verdict != 'digital':
        raise ValueError('pdf_kind says %r, not digital: this reader reads a text layer only' % verdict)
    import pdfplumber
    out = []
    with pdfplumber.open(os.path.join(ROOT, path)) as pdf:
        for pg in pdf.pages:
            words = sorted(pg.extract_words(), key=lambda w: (round(w['top']), w['x0']))
            lines = []
            for w in words:
                if lines and abs(w['top'] - lines[-1][0]) <= 3:
                    lines[-1][1].append(w)
                else:
                    lines.append([w['top'], [w]])
            out.append([(' '.join(w['text'] for w in sorted(ws, key=lambda w: w['x0'])),
                         [(w['text'], w['x1']) for w in sorted(ws, key=lambda w: w['x0'])]) for _, ws in lines])
    return out


def column_edges(page):
    """The five figure columns' right edges, MEASURED from this page's own full lines (median per
    position), so a page set differently needs no new constant."""
    full = [[x for t, x in ws if MONEY.fullmatch(t)] for _, ws in page]
    full = [f for f in full if len(f) == 5]
    if not full:
        return None
    return [sorted(f[i] for f in full)[len(full) // 2] for i in range(5)]


def parse(d):
    rows, totals, problems = [], {}, []
    section, cc, ccname = 'expenses', '', ''
    seen = {}
    edges = None
    for pno, page in enumerate(pages(d['path']), 1):
        edges = column_edges(page) or edges
        for line, words in page:
            line = line.strip()
            if not line or line.startswith(('FY26 FY26', 'DISTRICT EXPENSES', 'DESCRIPTION')) or re.match(r'^Page \d+$', line):
                continue
            if line == 'DISTRICT SALARIES':
                section, cc, ccname = 'salaries', '', ''
                continue
            toks = list(MONEY.finditer(line))
            h = HEADING.match(line)
            if h and not toks:
                cc, ccname = h.group(1), h.group(2).strip()
                continue
            label = (line[:toks[0].start()] if toks else line).strip().rstrip(':').strip()
            vals = [None] * 5
            for t, x in [(t, x) for t, x in words if MONEY.fullmatch(t)]:
                col = min(range(5), key=lambda i: abs(edges[i] - x))
                if vals[col] is not None:
                    problems.append('page %d: two figures under one column on %r' % (pno, line))
                vals[col] = num(t)
            tail = line[toks[-1].end():] if toks else ''
            pm = PCT.search(tail)
            if re.match(r'^TOTAL ', label, re.I):
                key = re.sub(r'\s+', ' ', label.upper())
                totals.setdefault(key, vals)
                continue
            sec = 'reserve' if label.lower() == 'salary reserve' else section   # printed after TOTAL SALARIES, in neither section total
            if sec == 'reserve':
                cc, ccname = '', ''
            k = (sec, cc, label)
            seen[k] = seen.get(k, 0) + 1
            r = dict(fy=d['fy'], version=d['version'], section=sec, cost_centre=cc, cost_centre_name=ccname,
                     line=label, ordinal=seen[k], document=d['path'], sha256=d['sha256'], page=pno,
                     pct_diff=pm.group(0) if pm else '')
            for i, c in enumerate(FIG):
                r[c] = vals[i]
            rows.append(r)
    return rows, totals, problems


DRAFT_COLS = ('fy27_budget', 'fy28_proposed', 'diff')      # what the draft PROPOSES: a miss here holds it
PRIOR_COLS = ('fy26_original', 'fy26_actual')              # the year already voted and spent, reprinted for reference
FOOT_COLS = ['fy', 'version', 'check', 'column', 'lines_sum', 'printed', 'difference', 'result']


def foot(d, rows, totals):
    """Rule 13. Every check becomes a row of the published footing record.

    A miss in a column the draft PROPOSES (FY27, FY28, $ Diff), or in any line's own identity,
    holds the draft. A miss in a PRIOR-YEAR column (FY26 original, FY26 actual) is the district's
    reprint of an earlier year disagreeing with itself: it is recorded at its full amount as a
    `printed defect` and shown on the page, never closed as rounding, and it does not hold the
    draft -- nothing the draft proposes rests on it, and the FY26 actual may never feed a headline
    (rule 1) in any case."""
    checks = []

    def close(check, column, got, want, line_level=False):
        diff = round(got - want, 2)
        if diff == 0:
            result = 'ties'
        elif abs(diff) <= 1.0:
            result = TOLERANCE_PHRASE
        elif column in PRIOR_COLS and not line_level:
            result = 'printed defect'
        else:
            result = 'FAILS'
        checks.append(dict(fy=d['fy'], version=d['version'], check=check, column=column,
                           lines_sum=round(got, 2), printed=want, difference=diff, result=result))

    n = bad = 0
    for r in rows:
        if r['diff'] is not None and r['fy28_proposed'] is not None and r['fy27_budget'] is not None:
            n += 1
            got, want = r['fy28_proposed'] - r['fy27_budget'], r['diff']
            if round(got - want, 2) != 0:
                bad += 1
                close('line %r (%s, page %d): FY28 - FY27 = $ Diff' % (r['line'], r['cost_centre'], r['page']), 'diff', got, want, True)
    checks.append(dict(fy=d['fy'], version=d['version'], check='%d lines printing a $ Diff: FY28 - FY27 = $ Diff' % n,
                       column='diff', lines_sum='', printed='', difference='', result='ties' if not bad else '%d do not' % bad))
    for sec, key in (('expenses', 'TOTAL EXPENSES'), ('salaries', 'TOTAL SALARIES')):
        want = totals.get(key) or totals.get(key + ':')
        if not want:
            checks.append(dict(fy=d['fy'], version=d['version'], check='printed ' + key, column='', lines_sum='',
                               printed='', difference='', result='FAILS'))
            continue
        for i, c in enumerate(FIG):
            close('%s lines against %s' % (sec, key), c, sum((r[c] or 0) for r in rows if r['section'] == sec), want[i] or 0)
    grand = totals.get('TOTAL ACTUALS & BUDGET') or totals.get('TOTAL ACTUALS & BUDGET:')
    if not grand:
        checks.append(dict(fy=d['fy'], version=d['version'], check='printed TOTAL ACTUALS & BUDGET', column='',
                           lines_sum='', printed='', difference='', result='FAILS'))
    else:
        for i, c in enumerate(FIG):
            close('every line, Salary Reserve included, against TOTAL ACTUALS & BUDGET', c,
                  sum((r[c] or 0) for r in rows), grand[i] or 0)
    fails = [c['check'] + ', ' + c['column'] + ': lines sum to %s, the document prints %s' % (format(c['lines_sum'], ',.2f'), format(c['printed'], ',.2f'))
             for c in checks if c['result'] == 'FAILS' and c['printed'] != '']
    fails += [c['check'] for c in checks if c['result'] == 'FAILS' and c['printed'] == '']
    return fails, checks


def build():
    out, held, report, footing = [], [], [], []
    for d in drafts():
        try:
            rows, totals, problems = parse(d)
        except Exception as e:                      # an unreadable draft is held, never skipped quietly
            held.append('FY%d Version %d (%s): unreadable: %s' % (d['fy'] % 100, d['version'], d['path'], e))
            continue
        fails, checks = foot(d, rows, totals)
        footing.extend(checks)
        fails = problems + fails
        if fails:
            held.append('FY%d Version %d (%s): does not foot -- %s' % (d['fy'] % 100, d['version'], d['path'], '; '.join(fails[:6])))
            continue
        tol = sum(1 for c in checks if c['result'] == TOLERANCE_PHRASE)
        defects = [c for c in checks if c['result'] == 'printed defect']
        report.append('FY%d Version %d: %d lines, %d cost centres; every proposed column and every line identity ties%s%s'
                      % (d['fy'] % 100, d['version'], len(rows), len({(r['section'], r['cost_centre']) for r in rows}),
                         ('; %d %s' % (tol, TOLERANCE_PHRASE)) if tol else '',
                         ''.join('; printed defect in %s: %s differs by $%.2f' % (c['column'], c['check'], abs(c['difference'])) for c in defects)))
        out.extend(rows)
    return out, held, report, footing


def fmt(v):
    if v is None:
        return ''
    if isinstance(v, float):
        return ('%.2f' % v).rstrip('0').rstrip('.') if v != int(v) else str(int(v))
    return str(v)


def render(rows, cols=COLS):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: fmt(r.get(k)) for k in cols})
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--index', help='a catalogue to read instead of the district\'s (a test fixture)')
    ap.add_argument('--out', help='a directory to write into instead of sources/data/budget-seasons (a test)')
    a = ap.parse_args()
    global INDEX, OUT, HELD, FOOTING
    if a.index:
        INDEX = os.path.abspath(a.index)
    if a.out:
        d = os.path.abspath(a.out)
        OUT, HELD, FOOTING = (os.path.join(d, os.path.basename(x)) for x in (OUT, HELD, FOOTING))
    rows, held, report, footing = build()
    text = render(rows)
    foot_text = render(footing, FOOT_COLS)
    held_text = ''.join(h + '\n' for h in held)
    for line in report:
        print(line)
    for h in held:
        print('HELD ' + h)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        have_f = open(FOOTING, encoding='utf-8').read() if os.path.exists(FOOTING) else ''
        ok = have == text and have_f == foot_text
        print('ok -- %s reproduces (%d lines)' % (os.path.relpath(OUT, ROOT), len(rows)) if ok else 'STALE ' + OUT)
        return 0 if ok else 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(text)
    open(FOOTING, 'w', encoding='utf-8').write(foot_text)
    if held:
        open(HELD, 'w', encoding='utf-8').write(held_text)
    elif os.path.exists(HELD):
        os.remove(HELD)
    print('%s: %d lines' % (os.path.relpath(OUT, ROOT), len(rows)))
    return 2 if held else 0


if __name__ == '__main__':
    raise SystemExit(main())
