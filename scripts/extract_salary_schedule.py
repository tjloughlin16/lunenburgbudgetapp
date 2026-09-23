#!/usr/bin/env python3
"""The Salary Administration Plan's grade and step table, and only the rates that PROVE.

    python3 scripts/extract_salary_schedule.py
    python3 scripts/extract_salary_schedule.py --check

Writes `sources/data/salary-schedule.csv` and `sources/data/salary-schedule-refused.csv`.

--------------------------------------------------------------------------------------
WHAT THIS TABLE IS, AND WHY IT IS FILED UNDER `payroll` BY MISTAKE
--------------------------------------------------------------------------------------

`annual-report-pages.csv` files these pages under the subject `payroll`. They are not
payroll. Payroll is what the town PAID somebody, name by name, and lives in
`report-gross-wages.csv`. This is the SCHEDULE the town votes: twenty grades by eight
steps of HOURLY RATES, adopted as a bylaw amendment inside a town-meeting article. It
says what a grade 9 step 3 post is worth per hour. It does not say that anybody holds
one, and rule 11's warning runs here too -- a rate is not a person and eight steps are
not eight employees.

--------------------------------------------------------------------------------------
THERE IS NO TOTAL ON THIS PAGE, SO THE PROOF HAD TO COME FROM SOMEWHERE ELSE
--------------------------------------------------------------------------------------

Every other table in this archive is published against an identity the document states
about itself -- a column that foots, a grand total, a balance that carries forward. A
grade/step schedule states none. It prints 160 rates and nothing that adds up.

So what proves a rate here is a SECOND PRINTING of it. Three things follow, and they are
the whole method:

**1. A figure off a PDF's text layer is not a reading.** It is the bytes the publisher
wrote. Where a schedule arrives that way -- FY2022 page 152, and both town-meeting
booklets -- there is nothing between us and the document and the rate is published as it
stands. Rule 13's warning is about an instrument that reformats before you see it; a text
layer is not an instrument.

**2. A figure off Apple Vision IS a reading, and needs a control.** FY2016 prints the
FY2017 schedule TWICE -- the Annual Town Meeting of 5 May 2016 on page 150 and the
Special Town Meeting of 28 November 2016 on page 186 -- and the two readings already
disagree: grade 3 step 1 comes back `$11.217` from page 150 and `$11.21` from page 186.
Three digits after the point is not a rate. The 2016 ATM booklet settles it in the text
layer, exactly: `3 $11.21 $11.55 $11.89 ...`.

**3. Where no second printing exists, the next year's schedule is one.** The FY2016
schedule is printed once in this archive, as a scan, in the FY2015 report. Its control is
the FY2017 schedule, which is exact -- because the article that adopts FY2017 says in the
town's own words what the relation between them is:

    "to replace the current Salary Schedule ... with the below FY'2017 Salary Schedule
     which authorises a cost of living increase of 2% per year for Fiscal Year 2017"
     -- 2016 ATM booklet, page 9, Article 16

A candidate FY2016 rate is confirmed when it reproduces the FY2017 rate at that 2%, to
the cent. That is not the same KIND of proof as a column that foots and it is not
presented as one: `confirmed_by` says which control cleared each rate, and a rate no
control clears is refused rather than published with a caveat.

**Thirteen of FY2016's 160 rates fail that control and are refused.** They fail by ONE
CENT: grade 2 step 3 reads $10.69, and $10.69 x 1.02 is $10.90 where the FY2017 schedule
prints $10.91. A cent is what you would expect if the town applied the increase to an
unrounded rate and rounded once at the end -- but nothing here tests that, and a rule
that accepts a cent of slack accepts a misread last digit with it. So those thirteen are
listed in the refusal file with the rate each one reads, and are not published.

**And this does not establish that the COLA was 2%.** The article states an intent and
rule 7 is explicit that intent is not outcome. What the arithmetic shows is narrower and
is all that is claimed: the scanned FY2016 figure and the printed FY2017 figure stand in
that relation, which a misread digit would break.

--------------------------------------------------------------------------------------
READING THE GRID
--------------------------------------------------------------------------------------

A salary schedule has NO GAPS: every grade prints all eight steps. That is what makes it
safe to take the rates of a row in printed order, which rule 13b otherwise forbids --
the rule exists because a row with an EMPTY cell puts every later figure under the wrong
heading, and here there are none. The guard is the count: a row is read only if it holds
exactly eight rates, and refused with its own text if it does not. Nothing is placed by
guessing which step a lone figure belongs to.

Two things the Vision cache does to this page that a reader should know about:

  * it splits a rate from its currency sign, so `$` and `12.01` arrive as separate
    observations, and sometimes reads the sign as `S` or `Ş`;
  * it merges six rates into one observation --
    `$ 9.81 $ 10.11 $ 10.41 $ 10.72 $ 11.04 $ 11.38` is one box on FY2015 page 198.

Both are handled by matching rates in the text of every box on the row and ordering by
the box's x. The sign is not needed to find a rate and is not used.
"""
import argparse
import collections
import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
REPORTS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
BOOKLETS = os.path.join(ROOT, 'sources', 'town-budget', 'docs')

OUT = os.path.join(ROOT, 'sources', 'data', 'salary-schedule.csv')
OUT_REFUSED = os.path.join(ROOT, 'sources', 'data', 'salary-schedule-refused.csv')

FIELDS = ['report_fy', 'document', 'page', 'schedule_fy', 'grade', 'step', 'rate',
          'basis', 'confirmed_by']
REFUSED_FIELDS = ['report_fy', 'document', 'page', 'subject', 'reason', 'evidence']

# WHERE THE SCHEDULE IS PRINTED. Each entry is a printing, not a year: FY2017 is printed
# three times and the three are what check each other. `report_fy` is the fiscal year of
# the DOCUMENT the page sits in -- never the year the schedule is for, which is
# `schedule_fy` and is read off the page's own heading.
PRINTINGS = [
    # report_fy, document, page, where the file lives, how it is read
    ('2015', '4121-fy-2015-annual-town-report.pdf', 198, REPORTS, 'ocr'),
    ('2016', '4123-fy-2016-annual-town-report.pdf', 150, REPORTS, 'ocr'),
    ('2016', '4123-fy-2016-annual-town-report.pdf', 186, REPORTS, 'ocr'),
    ('2022', '4129-fy-2022-annual-town-report.pdf', 152, REPORTS, 'text'),
    ('2016', 'a163-2016-may-annual-town-meeting-booklet-pdf.pdf', 9, BOOKLETS, 'text'),
    ('2022', 'a170-2022-may-annual-town-meeting-booklet-pdf.pdf', 28, BOOKLETS, 'text'),
]

# The relation the adopting article states between one schedule and the year before it.
# Only used to CONFIRM a scanned reading against an exact one; never to compute a rate.
STATED_COLA = {
    ('2016', '2017'): (0.02, "the FY2017 article's stated 2% cost of living increase "
                             "(2016 ATM booklet, page 9, Article 16)"),
}

RATE = re.compile(r'\b(\d{1,3}\.\d{2})\b')
GRADE = re.compile(r'^(\d{1,2})$')


def load_ocr(path, page):
    """Vision boxes for one page. Tab split -- never csv.DictReader, and never QUOTE_NONE
    by accident: OCR text carries bare `"` and the csv module then swallows whole pages.
    """
    out = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        for i, line in enumerate(fh):
            f = line.rstrip('\n').split('\t')
            if i == 0 or len(f) < 7:
                continue
            try:
                p, x, y, w, h = int(f[0]), float(f[1]), float(f[2]), float(f[3]), float(f[4])
            except ValueError:
                continue
            if p == page:
                out.append({'x': x, 'y': y, 'w': w, 'h': h, 't': '\t'.join(f[6:]).strip()})
    return out


def ocr_rows(boxes):
    """The grid's rows, banded at half the page's own row pitch -- rule 13b, measured."""
    ys = sorted({round(b['y'], 4) for b in boxes}, reverse=True)
    gaps = [a - b for a, b in zip(ys, ys[1:]) if 0.002 < a - b < 0.08]
    band = (sorted(gaps)[len(gaps) // 2] / 2.0) if gaps else 0.006
    boxes = sorted(boxes, key=lambda b: (-b['y'], b['x']))
    rows = []
    for b in boxes:
        if rows and abs(b['y'] - rows[-1][0]['y']) < band:
            rows[-1].append(b)
        else:
            rows.append([b])
    for r in rows:
        r.sort(key=lambda b: b['x'])
    return rows


def grid_from_ocr(path, page, refuse):
    """Grade -> eight rates, off the scanned grid, plus the schedule's own year."""
    boxes = load_ocr(path, page)
    if not boxes:
        return None, {}
    text = ' '.join(b['t'] for b in boxes)
    m = re.search(r'FOR FISCAL YEAR\s*(\d{4})', text, re.I)
    sched = m.group(1) if m else None
    # THE GRID IS PART OF A PAGE, NOT THE PAGE. On FY2016 pages 150 and 186 the schedule
    # sits inside a town-meeting article, so the rows below it are prose -- and a
    # sentence like `the sum of $110,142.36 to supplement the amounts` holds something
    # that looks exactly like an hourly rate. The grid is bounded at the top by its own
    # printed header (`Grade  Step 1 ... Step 8`) and at the bottom by the first line of
    # running text, rather than by hunting for rate-shaped strings anywhere on the sheet.
    rows = ocr_rows(boxes)
    top = next((i for i, r in enumerate(rows)
                if 'grade' in ' '.join(b['t'] for b in r).lower()
                and 'step 1' in ' '.join(b['t'] for b in r).lower()), None)
    if top is None:
        return sched, {}
    grid_rows = []
    for r in rows[top + 1:]:
        # 70 characters, not 40: a merged observation of six rates is 45 characters
        # long (`$ 9.81 $ 10.11 $ 10.41 $ 10.72 $ 11.04 $ 11.38`, FY2015 page 198,
        # grade 1) and a line of the article's prose is 110.
        if max((len(b['t']) for b in r), default=0) > 70:
            break
        grid_rows.append(r)
    out, last = {}, 0
    for row in grid_rows:
        rates = []
        for b in row:
            rates += [float(v) for v in RATE.findall(b['t'])]
        if not rates:
            continue
        head = row[0]['t'].strip()
        gm = GRADE.match(head)
        grade = int(gm.group(1)) if gm else last + 1
        if len(rates) != 8:
            refuse.append(('a grade row does not hold eight rates',
                           'grade %s reads %d: %s' % (head or '?', len(rates),
                                                      ' '.join('%.2f' % v for v in rates))))
            continue
        if not 1 <= grade <= 30 or grade in out:
            continue
        out[grade] = rates
        last = grade
    return sched, out


def grid_from_text(folder, doc, page, refuse):
    """Grade -> eight rates, off the PDF's own text layer. Not a reading -- the bytes."""
    import pdfplumber
    with pdfplumber.open(os.path.join(folder, doc)) as pdf:
        lines = (pdf.pages[page - 1].extract_text() or '').split('\n')
    sched = None
    for ln in lines:
        m = re.search(r'FISCAL YEAR\s*(\d{4})', ln, re.I) or re.search(r'FY\s*(\d{4})', ln)
        if m:
            sched = m.group(1)
            break
    out = {}
    for ln in lines:
        parts = ln.split()
        if not parts or not GRADE.match(parts[0]):
            continue
        rates = [float(v) for v in RATE.findall(ln[len(parts[0]):])]
        grade = int(parts[0])
        if len(rates) != 8:
            if len(rates) > 2:
                refuse.append(('a grade row does not hold eight rates',
                               'line reads %r' % ln[:90]))
            continue
        if 1 <= grade <= 30 and grade not in out:
            out[grade] = rates
    return sched, out


def read(printings, refused):
    """Every printing, as {schedule_fy: [(printing, grid)]}."""
    by_year = collections.defaultdict(list)
    for report_fy, doc, page, folder, how in printings:
        refuse = []
        if how == 'ocr':
            tsv = os.path.join(OCR, doc[:-4] + '.tsv')
            if not os.path.exists(tsv):
                refused.append({'report_fy': report_fy, 'document': doc, 'page': page,
                                'subject': 'payroll',
                                'reason': 'the page has no Vision reading in the archive',
                                'evidence': 'expected %s'
                                            % os.path.relpath(tsv, ROOT)})
                continue
            sched, grid = grid_from_ocr(tsv, page, refuse)
            basis = 'Apple Vision OCR'
        else:
            sched, grid = grid_from_text(folder, doc, page, refuse)
            basis = 'PDF text layer'
        for reason, evidence in refuse:
            refused.append({'report_fy': report_fy, 'document': doc, 'page': page,
                            'subject': 'payroll', 'reason': reason, 'evidence': evidence})
        if not sched or not grid:
            refused.append({'report_fy': report_fy, 'document': doc, 'page': page,
                            'subject': 'payroll',
                            'reason': 'no grade and step grid could be read off the page',
                            'evidence': 'schedule year %r, %d grade rows'
                                        % (sched, len(grid))})
            continue
        by_year[sched].append({'report_fy': report_fy, 'document': doc, 'page': page,
                               'basis': basis, 'grid': grid})
    return by_year


def confirm(by_year):
    """What independently agrees with each scanned rate, or nothing.

    Two controls, in this order, and a rate takes the first that clears it:

      1. ANOTHER PRINTING OF THE SAME SCHEDULE. Exact equality, no tolerance. Where one
         of the two is a text layer that is as good as this archive gets.
      2. THE NEXT YEAR'S SCHEDULE at the cost of living increase its adopting article
         states, where that next year is itself exact.
    """
    exact = {}
    for year, prints in by_year.items():
        for p in prints:
            if p['basis'] == 'PDF text layer':
                exact.setdefault(year, p)
    who = {}
    for year, prints in by_year.items():
        for p in prints:
            for grade, rates in p['grid'].items():
                for step, rate in enumerate(rates, 1):
                    key = (year, p['document'], p['page'], grade, step)
                    if p['basis'] == 'PDF text layer':
                        who[key] = 'the document itself; no reading was involved'
                        continue
                    for q in prints:
                        if q is p:
                            continue
                        other = q['grid'].get(grade, [None] * 8)[step - 1]
                        if other is not None and abs(other - rate) < 0.0005:
                            who[key] = ('%s page %d, which prints the same schedule (%s)'
                                        % (q['document'], q['page'], q['basis'].lower()))
                            break
                    if key in who:
                        continue
                    for (a, b), (cola, said) in STATED_COLA.items():
                        if a != year or b not in exact:
                            continue
                        nxt = exact[b]['grid'].get(grade, [None] * 8)[step - 1]
                        if nxt is not None and abs(round(rate * (1 + cola), 2) - nxt) < 0.005:
                            who[key] = ('the FY%s schedule in %s page %d, at %s'
                                        % (b, exact[b]['document'], exact[b]['page'], said))
                            break
    return who


def write(path, fields, rows, check):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    if check:
        cur = open(path, encoding='utf-8', newline='').read() if os.path.exists(path) else ''
        if cur != buf.getvalue():
            print('  STALE: %s -- run python3 scripts/extract_salary_schedule.py'
                  % os.path.relpath(path, ROOT))
            return 1
        print('  %s is current' % os.path.relpath(path, ROOT))
        return 0
    open(path, 'w', encoding='utf-8', newline='').write(buf.getvalue())
    print('wrote %s (%d rows)' % (os.path.relpath(path, ROOT), len(rows)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    refused = []
    by_year = read(PRINTINGS, refused)
    who = confirm(by_year)

    rows, unproven = [], collections.defaultdict(list)
    for year in sorted(by_year):
        for p in sorted(by_year[year], key=lambda p: (p['report_fy'], p['page'])):
            for grade in sorted(p['grid']):
                for step, rate in enumerate(p['grid'][grade], 1):
                    key = (year, p['document'], p['page'], grade, step)
                    if key not in who:
                        unproven[(p['report_fy'], p['document'], p['page'])].append(
                            'grade %d step %d reads %.2f' % (grade, step, rate))
                        continue
                    rows.append({'report_fy': p['report_fy'], 'document': p['document'],
                                 'page': p['page'], 'schedule_fy': year, 'grade': grade,
                                 'step': step, 'rate': '%.2f' % rate,
                                 'basis': p['basis'], 'confirmed_by': who[key]})
    for (fy, doc, page), bad in sorted(unproven.items()):
        refused.append({'report_fy': fy, 'document': doc, 'page': page,
                        'subject': 'payroll',
                        'reason': 'no second printing confirms these rates, and the page '
                                  'prints no total to foot them against',
                        'evidence': '%d rates unconfirmed: %s' % (len(bad), '; '.join(bad))})
    refused.sort(key=lambda r: (r['report_fy'], str(r['page']), r['reason']))

    print('SALARY ADMINISTRATION PLAN: %d rates published, %d schedule years, '
          '%d printings' % (len(rows), len({r['schedule_fy'] for r in rows}),
                            len({(r['document'], r['page']) for r in rows})))
    for year in sorted(by_year):
        got = [r for r in rows if r['schedule_fy'] == year]
        print('  FY%s: %d printings, %d of %d rates published'
              % (year, len(by_year[year]), len(got),
                 sum(8 * len(p['grid']) for p in by_year[year])))
    print('  %d refusals' % len(refused))
    for r in refused:
        print('    FY%s page %s: %s -- %s'
              % (r['report_fy'], r['page'], r['reason'], r['evidence']))

    rc = write(OUT, FIELDS, rows, a.check)
    rc |= write(OUT_REFUSED, REFUSED_FIELDS, refused, a.check)
    return rc


if __name__ == '__main__':
    sys.exit(main())
