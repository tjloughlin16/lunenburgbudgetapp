"""The Program of Capital Projects the town meeting was asked to choose between.

    python3 scripts/extract_capital_options.py
    python3 scripts/extract_capital_options.py --check

Writes `sources/data/capital-program-options.csv`.

WHAT THIS IS, AND WHY IT IS WORTH READING

The warrant does not put one capital plan to the meeting. It puts TWO, priced to the same
total, and asks which one. FY2026 Option 1 funds twenty projects; Option 2 funds fifteen of
the same twenty, drops five, and adds one the other does not have -- a Primary School heat
pump system carried as a local match for a Green Communities award. Both land on
$1,225,000.

So this is the clearest published statement in the archive of what the town CHOSE not to
buy, at a moment when it was choosing. Rule 8: the job is what the options cost somebody,
not what anybody got wrong.

The pages were filed under `appropriations` because the page above them is an article, and
the appropriations reader takes a page of articles. Neither option table was held anywhere.

WHAT PROVES IT

The table prints a running `Cumulative Cost` beside every project cost, and a `Total` at the
foot. Two identities, and both must hold before anything is written:

    every cumulative   = the cumulative above it plus this project's cost
    the last cumulative = the printed Total

A running total is a strong check on a list, because it is a separate assertion at EVERY
row rather than one at the bottom: a figure misread in line 9 breaks lines 9 through 20, and
a line dropped altogether breaks every line after it. A single grand total would absorb a
row read twice against a row not read at all; this cannot.

THE RANKINGS HAVE GAPS, AND THAT IS THE DATA, NOT A LOSS. Option 1 runs 1,2,3...13,15,16,17,
19,20,22 -- there is no 14, 18 or 21 -- and Option 2 is sparser still. They are CPC rankings
of a longer list than either option funds, so a gap is a project ranked and not carried. The
cumulative chain is what makes that safe to say: if a row had been missed rather than never
printed, the chain would break at it.

`N/A` is a real ranking value. The Green Communities match on Option 2 carries no CPC rank,
and coercing it to a number would invent one.
"""
import argparse
import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'capital-program-options.csv')

MONEY = re.compile(r'^\$[\d,]+$')
HEAD = re.compile(r'Program\s+of\s+Capital\s+Projects\s+Option\s+(\d)', re.I)
FIELDS = ['report_fy', 'program_fy', 'option', 'cpc_ranking', 'department', 'project',
          'project_cost', 'cumulative_cost', 'kind', 'proof', 'page', 'document']

EDITIONS = {2025: 'sources/town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf'}

# The column the figure sits in decides what it IS, and these are read off the page: the
# project cost is printed at x 424-430 and the cumulative at x 486-501. Placing by ORDER
# would work until a row printed no project cost -- which the `Total` row does.
COST_X = (400, 470)
CUM_X = (470, 560)
RANK_X = 115           # the CPC ranking sits left of this
DEPT_X = 200           # the department between RANK_X and this; the project name after it


def lines_of(page):
    """The page's printed lines. The pitch is ~14pt and a wrapped project name is a line of
    its own, so nothing here may merge two."""
    band = {}
    for w in page.extract_words():
        band.setdefault(round(w['top'] / 6.0), []).append(w)
    return [sorted(v, key=lambda w: w['x0']) for _, v in sorted(band.items())]


def num(t):
    return int(t.replace('$', '').replace(',', ''))


def read_options(pdf):
    import pdfplumber
    out = []
    with pdfplumber.open(pdf) as doc:
        for i, page in enumerate(doc.pages):
            lines = lines_of(page)
            opt = None
            pending, rows = [], []
            for ln in lines:
                text = ' '.join(w['text'] for w in ln)
                m = HEAD.search(text)
                if m:
                    if opt and rows:
                        out.append((i + 1, opt, rows))
                    opt, rows, pending = m.group(1), [], []
                    continue
                if opt is None:
                    continue
                figs = [w for w in ln if MONEY.match(w['text'])]
                if not figs:
                    # A WRAPPED PROJECT NAME, held for the line that carries the figures.
                    # `Primary School Feasibility Study for` sits above `Entry & Drive Way
                    # Expansion`, and dropping it truncates the project to its second half.
                    if ln and all(w['x0'] >= DEPT_X for w in ln) and len(rows) or (
                            ln and all(w['x0'] >= DEPT_X for w in ln)):
                        pending.append(text)
                    continue
                cost = next((num(w['text']) for w in figs
                             if COST_X[0] <= w['x0'] < COST_X[1]), None)
                cum = next((num(w['text']) for w in figs
                            if CUM_X[0] <= w['x0'] < CUM_X[1]), None)
                if cum is None:
                    pending = []
                    continue
                rank = ' '.join(w['text'] for w in ln if w['x0'] < RANK_X)
                dept = ' '.join(w['text'] for w in ln
                                if RANK_X <= w['x0'] < DEPT_X)
                name = ' '.join(pending + [' '.join(
                    w['text'] for w in ln
                    if DEPT_X <= w['x0'] < COST_X[0])]).strip()
                pending = []
                rows.append(dict(cpc_ranking=rank.strip(), department=dept.strip(),
                                 project=' '.join(name.split()),
                                 project_cost=cost, cumulative_cost=cum))
            if opt and rows:
                out.append((i + 1, opt, rows))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    body = []
    for report_fy, rel in sorted(EDITIONS.items()):
        pdf = os.path.join(ROOT, rel)
        for page, opt, rows in read_options(pdf):
            total = next((r for r in rows if r['project_cost'] is None
                          and re.match(r'^Total\b', r['project'], re.I)), None)
            items = [r for r in rows if r is not total]
            if total is None or len(items) < 5:
                print('p%d Option %s: %d lines, total=%s -- not the option table'
                      % (page, opt, len(items), total), file=sys.stderr)
                continue

            # THE RUNNING TOTAL, ROW BY ROW. Nothing is written unless every step closes.
            bad, run = [], 0
            for r in items:
                run += r['project_cost']
                if run != r['cumulative_cost']:
                    bad.append('%s: %d + %d = %d against a printed %d (%+d)'
                               % (r['project'][:44], run - r['project_cost'],
                                  r['project_cost'], run, r['cumulative_cost'],
                                  run - r['cumulative_cost']))
            if run != total['cumulative_cost']:
                bad.append('Total: the %d projects sum to %d against a printed %d (%+d)'
                           % (len(items), run, total['cumulative_cost'],
                              run - total['cumulative_cost']))
            if bad:
                print('FY%d p%d Option %s does not close, nothing written:\n  %s'
                      % (report_fy, page, opt, '\n  '.join(bad[:8])), file=sys.stderr)
                return 1

            proof = ('every cumulative is the one above plus this project, and the last '
                     'is the printed Total')
            for r in items + [total]:
                body.append(dict(
                    report_fy=report_fy, program_fy=report_fy + 1, option=int(opt),
                    kind='total' if r is total else 'project', proof=proof,
                    page=page, document=os.path.relpath(pdf, ROOT), **r))

    if not body:
        print('no capital option table found', file=sys.stderr)
        return 1

    body.sort(key=lambda r: (r['report_fy'], r['option'], r['cumulative_cost']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    for r in body:
        wr.writerow({k: ('' if r.get(k) is None else r.get(k)) for k in FIELDS})
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/extract_capital_options.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d lines, every running total closes' % len(body))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote %s -- %d lines' % (os.path.relpath(OUT, ROOT), len(body)))
    for o in sorted({(r['report_fy'], r['option'], r['page']) for r in body}):
        n = [r for r in body if r['option'] == o[1] and r['kind'] == 'project']
        print('  FY%d p%d  Option %d: %d projects, $%s'
              % (o[0], o[2], o[1], len(n), format(max(r['cumulative_cost'] for r in n), ',')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
