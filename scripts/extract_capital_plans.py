#!/usr/bin/env python3
"""The Capital Planning Committee's recommended plan, year by year, from the town reports.

`capital_projects` in `extract_tables.py` reads a different thing: the capital project
FUND balance schedule -- what was appropriated, spent and left. This reads what the Capital
Planning Committee RECOMMENDED for the coming year, which is the ranked list of projects
the town then votes on. `sources/data/capital-plan-fy27.csv` already holds one year of it,
taken from the FY27 capital plan document. The annual town reports carry the same table
for every year back to the FY2015 plan, and none of it had been read.

**Every layout is different and the column ruler is the only thing that survives.** In one
decade the table has been printed with a department column and no ranks, with ranks and a
running cumulative, with two competing rank columns (the Town Manager's and the
Committee's), and with a category column. The heading words differ every year. So no
heading is matched and no column is named by position. Instead:

**The cost column is the one that foots to the total the page prints.** Every money column
on the page is ruled out or in by that single test -- a ranked list of projects has exactly
one column whose figures sum to the plan total, and a cumulative column gives itself away
by ENDING at the total instead. A page where no column foots is refused and named, rather
than read into rows nobody can check.

That is the whole safety property here, and it is worth stating plainly: a wrong column
cannot sum to the right total. It is rule 13b's argument for OCR, applied to a choice of
column instead of a choice of row.

**The plan is printed twice in most reports** -- once in the Committee's own report and
again inside the Annual Town Meeting article that funds it. Both are read, and the two are
compared: a project that appears in one and not the other, or at a different figure, is
the difference between what was recommended and what was put to the meeting.

    python3 scripts/extract_capital_plans.py
    python3 scripts/extract_capital_plans.py --check
"""

import argparse
import collections
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_valuation import pages_of, text_of, num  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'capital-plans.csv')
# A page this could not read is NOT a reading of it, and it must not be filed as one.
# `map_annual_report_pages.py` marks a queued page read when any dataset holds a row
# citing `report_fy` and `page` -- so a refusal row sitting in the dataset would clear the
# page from the queue while holding none of its figures, which is the same silent zero
# rule 13c is about. Refusals go in their own file, and that file carries a `state`
# column, which is the flag the join uses to skip a catalogue of what HAS been read
# rather than a reading.
REFUSED = os.path.join(ROOT, 'sources', 'data', 'capital-plans-refused.csv')
REFUSED_FIELDS = ['dataset', 'edition', 'report_fy', 'document', 'page', 'state',
                  'printed_total', 'columns_as_printed', 'reconciliation']

# `report_fy` and `page` are the join keys `map_annual_report_pages.py` reads to mark a
# queued page read. `plan_fiscal_year` is the year the PLAN is for -- one later than the
# report that prints it -- and must never be mistaken for the first.
FIELDS = ['dataset', 'edition', 'report_fy', 'document', 'page', 'copy',
          'plan_fiscal_year',
          'line_no', 'project', 'cost', 'cumulative', 'printed_total',
          'columns_as_printed', 'status', 'reconciliation']

# Lines that carry money and are not projects: the funding block printed under the plan,
# the headings, and the total itself. Every one of these sits in the same columns as the
# projects, so leaving them in puts the funding of the plan INSIDE the plan.
SKIP = re.compile(r'^\s*(\[?total|funding|free\s*cash|raise\s*&|raise and|unexpended|'
                  r'premium|special purpose|surplus|priority|project\s*#|cip#|dept\.|'
                  r'department\b|category|fiscal year|below is|at the annual|'
                  r'more information|the capital planning|the committee|cumulative)',
                  re.I)

# `$ 36,524` arrives as ONE box with a space inside it on the FY2014 page, and
# `58.000.00` is how that page's neighbour prints a thousands separator. Both are
# figures; a pattern that admits neither loses most of a table and says nothing.
MONEY_TOKEN = re.compile(r'^\$?[\d][\d,.]*$')

TOTAL_LINE = re.compile(r'^\[?Total(?:\s+Capital\s+Plan|\s+Available\s+Funding)?\s*'
                        r'\$?\s*([\d][\d,]*\.?\d*)\s*$', re.I)
TOTALING = re.compile(r'totaling\s+\$\s?([\d][\d,]*\.?\d*)')


def money_words(line):
    """The money tokens on a line, with a lone `$` glued to the figure it introduces.

    The OCR splits `$ 20,000` into two boxes on the FY2014 page and keeps `$20,000`
    whole on the FY2020 one. Read literally, the first loses every figure on the page.
    """
    out = []
    for i, w in enumerate(line):
        t = w['text'].strip().replace(' ', '')
        if t in ('$', 'S') and i + 1 < len(line):
            continue
        if MONEY_TOKEN.match(t) and num(t) is not None:
            out.append(dict(w, text=t))
    return out


def printed_total(lines):
    for i, line in enumerate(lines):
        t = text_of(line).strip()
        m = TOTAL_LINE.match(t)
        if m:
            return num(m.group(1)), t
        # `Total   $520,214` arrives as two boxes far apart on the FY2018 page.
        if re.match(r'^\[?Total(\s+Capital\s+Plan|\s+Available\s+Funding)?$',
                    ' '.join(w['text'] for w in line
                             if not MONEY_TOKEN.match(w['text'].strip())).strip(), re.I):
            mv = money_words(line)
            if len(mv) == 1:
                return num(mv[0]['text']), t
            # FY2018 prints the word and the figure on separate lines -- the total is
            # set above its own label. Looked for on either side, never further.
            for j in (i - 1, i + 1):
                if 0 <= j < len(lines):
                    near = money_words(lines[j])
                    if len(near) == 1 and len(lines[j]) == 1:
                        return num(near[0]['text']), t
    for line in lines:
        m = TOTALING.search(text_of(line))
        if m:
            return num(m.group(1)), text_of(line).strip()
    return None, ''


def before_the_total(lines):
    """Everything above the plan's own total line. The funding block sits below it.

    The block that says how the plan is PAID FOR -- free cash, raise and appropriate,
    unexpended capital -- prints in the same columns as the projects, so a figure from it
    read as a project silently breaks the one check this extractor has. Excluding it by
    its labels does not survive contact with the documents: the FY2021 article prints
    `Uhexpended Capital`, and a misspelling in a list of exclusions is invisible.

    The plan's total is the boundary, and it is a position rather than a word.
    """
    for i, line in enumerate(lines):
        t = text_of(line).strip()
        if re.match(r'^\[?Total\b', t, re.I):
            return lines[:i]
    return lines


def columns(rows, gap=0.05):
    cs = sorted(w['cx'] for _, mv in rows for w in mv)
    if not cs:
        return []
    cols, cur = [], [cs[0]]
    for c in cs[1:]:
        if c - cur[-1] > gap:
            cols.append(cur)
            cur = []
        cur.append(c)
    cols.append(cur)
    return [(sum(c) / len(c), len(c)) for c in cols]


def column_values(rows, centre, gap=0.04):
    """One column's figure per row, placed by position and absent where absent."""
    out = []
    for text, mv in rows:
        pick = raw = None
        for w in mv:
            if abs(w['cx'] - centre) <= gap:
                pick, raw = num(w['text']), w['text']
                break
        out.append((strip_figure(text, raw), pick))
    return out


def strip_figure(text, raw):
    """Take the cost out of the project's name, and ONLY the cost.

    The FY2014 table prints department, amount, item -- so the figure is in the MIDDLE of
    the line and a rule that trims trailing digits leaves `School $138,000 School
    Asbestos` as a project name. Stripping every number instead would rename `Police
    Vehicle, 1 marked` and `Engine 4 Replacement (1995)`, which is worse: those digits are
    the project.

    So exactly the token that was read as this row's figure is removed, with the dollar
    sign in front of it, and nothing else.
    """
    if not raw:
        return text
    body = raw[1:] if raw.startswith(('$', 'S')) else raw
    pat = r'\$?\s*' + re.escape(body).replace(r'\,', r'\s*,\s*') + r'(?![\d])'
    out = re.sub(pat, ' ', text, count=1)
    return re.sub(r'\s+', ' ', out).strip()


def read_plan(edition, doc, page, lines):
    total, total_text = printed_total(lines)
    if total is None:
        return []
    # Two readings of the page: everything above its total line, and the whole page.
    # Cutting at the total keeps the funding block out (FY2021), and on a page whose
    # plan CONTINUES from the one before it that cut removes the table (FY2022 p142).
    # The printed total settles which reading is right, as it settles everything else
    # here -- so both are tried and the one that foots is the one used.
    rows = cols = cost_col = cumulative_col = None
    for candidate in (before_the_total(lines), lines):
        rows = []
        for line in candidate:
            t = text_of(line).strip()
            if SKIP.match(t) or not re.search(r'[A-Za-z]{3}', t):
                continue
            mv = money_words(line)
            if mv:
                rows.append((t, mv))
        if len(rows) < 5:
            continue
        cols = columns(rows)
        cost_col = cumulative_col = None
        for centre, _ in cols:
            vals = [v for _, v in column_values(rows, centre) if v is not None]
            if not vals:
                continue
            if abs(sum(vals) - total) < 1:
                cost_col = centre
            elif abs(max(vals) - total) < 1 and vals == sorted(vals) and len(vals) > 3:
                cumulative_col = centre
        if cost_col is not None or cumulative_col is not None:
            break
    if not rows:
        return []
    if cost_col is None:
        # A cumulative column that ENDS at the total, with no column that sums to it,
        # still names every cost: the differences between consecutive cumulatives are
        # the costs, and the last one is the total itself. FY2018 is read this way,
        # because two of its cost cells print as `$112,00` and `$130,00`.
        if cumulative_col is not None:
            return from_cumulative(edition, doc, page, rows, cumulative_col, total,
                                   total_text)
        return [{'dataset': 'capital_plan', 'edition': edition, 'document': doc,
                 'page': page, 'project': '', 'printed_total': total,
                 'kind': 'refused', 'state': 'refused',
                 'status': 'check failed', 'columns_as_printed': total_text,
                 'reconciliation': (f'{len(rows)} candidate rows ruled into {len(cols)} '
                                    f'money columns and none of them sums to the printed '
                                    f'{total:,.2f}; refused rather than read')}]
    costs = column_values(rows, cost_col)
    cums = column_values(rows, cumulative_col) if cumulative_col is not None else None
    out = []
    n = 0
    for i, (text, cost) in enumerate(costs):
        if cost is None:
            continue
        n += 1
        out.append({'dataset': 'capital_plan', 'edition': edition, 'document': doc,
                    'page': page, 'line_no': n, 'project': clean(text),
                    'cost': cost,
                    'cumulative': cums[i][1] if cums else '',
                    'printed_total': total, 'columns_as_printed': total_text,
                    'status': 'checked',
                    'reconciliation': (f'{n} project rows; the column sums to '
                                       f'{total:,.2f} = the total the page prints')})
    for r in out:
        r['reconciliation'] = (f'{n} project rows sum to {total:,.2f} = the total the '
                               f'page prints')
    return out


def from_cumulative(edition, doc, page, rows, centre, total, total_text):
    """Costs recovered as the DIFFERENCES of a running total that ends where it should.

    FY2018 prints a cost and a cumulative side by side and truncates two of the costs --
    `$112,00` and `$130,00`, both a digit short. The cumulative column is unharmed, runs
    monotonically and finishes at the $520,214 the page prints, so each cost is the step
    between two cumulatives and the truncated cells are repaired by the column itself.
    """
    vals = [(t, v) for t, v in column_values(rows, centre) if v is not None]
    out, prev = [], 0.0
    for i, (text, cum) in enumerate(vals, 1):
        out.append({'dataset': 'capital_plan', 'edition': edition, 'document': doc,
                    'page': page, 'line_no': i, 'project': clean(text),
                    'cost': round(cum - prev, 2), 'cumulative': cum,
                    'printed_total': total, 'columns_as_printed': total_text,
                    'status': 'checked'})
        prev = cum
    note = (f'no column sums to the printed {total:,.2f}; the running CUMULATIVE column '
            f'does end there, over {len(out)} rows, so each cost is read as the step '
            f'between two cumulatives')
    for r in out:
        r['reconciliation'] = note
    return out


def clean(text):
    """Trim the leading rank columns and any trailing cumulative figure."""
    t = re.sub(r'\s*\$?\s*[\d][\d,]*\.?\d*\s*$', '', text).strip()
    t = re.sub(r'^(?:[\d]{1,3}[|\s]+){1,3}', '', t)
    return re.sub(r'\s+', ' ', t)[:120]


def plan_pages(pages):
    """Pages that carry a capital plan, found by what they PRINT, not by a page number.

    Located by the two things every version of this table has: the words `Capital Plan`
    or `Capital Program` somewhere on the page, and a total the page states. Page numbers
    move by thirty between editions and the heading is spelled `CAPTIAL PLANNING REPORT`
    in one of them.
    """
    out = []
    for p, lines in sorted(pages.items()):
        txt = ' | '.join(text_of(line) for line in lines)
        if not re.search(r'Cap(it|ti)al (Plan|Program|Planning)', txt, re.I):
            continue
        total, _ = printed_total(lines)
        if total is None or total < 100000:
            continue
        money_rows = sum(1 for line in lines
                         if money_words(line) and re.search(r'[A-Za-z]{3}',
                                                            text_of(line)))
        if money_rows < 8:
            continue
        # A page that merely MENTIONS the capital plan is not the capital plan. The
        # table announces itself in a heading -- `CAPITAL PLANNING`, `Fiscal Year 2025
        # Capital Plan`, `FY 2026 Program of Capital Projects` -- or, where the article
        # reprints it with no heading of its own, in a `Total Capital Plan` line.
        heads = [line for line in lines
                 if len(text_of(line).strip()) < 75
                 and re.search(r'Cap(it|ti)al (Plan|Program)|Program of Capital',
                               text_of(line), re.I)]
        if heads or re.search(r'Total (Capital Plan|Available Funding)', txt, re.I):
            out.append(p)
    return out


def copy_of(lines):
    """Which of the two printings this is.

    The Committee's own report and the Annual Town Meeting article that funds it carry
    the same table. Told apart by the article number, which only one of them has -- not
    by which comes first in the book, because in the FY2019 report the article's copy is
    the one on the later page and in the FY2018 report it is not.
    """
    for line in lines:
        if re.search(r'\bARTICLE\s+\d', text_of(line)):
            return 'town meeting article'
    return 'committee report'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    rows, refused = [], []
    for tsv in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        name = os.path.basename(tsv)
        m = re.search(r'fy-?(\d{4})', name)
        if not m:
            continue
        edition, doc = 'FY' + m.group(1), name.replace('.tsv', '.pdf')
        pages = pages_of(tsv)
        found = []
        for p in plan_pages(pages):
            got = read_plan(edition, doc, p, pages[p])
            if got:
                found.append((p, got))
        # The report's own section comes first; the town-meeting article reprints it.
        for p, got in found:
            for r in got:
                r['report_fy'] = m.group(1)
                r['copy'] = copy_of(pages[p])
                r['plan_fiscal_year'] = str(int(m.group(1)) + 1)
                if r.get('kind') == 'refused':
                    refused.append({k: r.get(k, '') for k in REFUSED_FIELDS})
                else:
                    rows.append({k: r.get(k, '') for k in FIELDS})

    rows.sort(key=lambda r: (r['edition'], int(r['page']),
                             int(r['line_no'] or 0)))
    refused.sort(key=lambda r: (r['edition'], int(r['page'])))

    if args.check:
        if not os.path.exists(OUT):
            sys.exit(f'{OUT} does not exist')
        for path, want in ((OUT, rows), (REFUSED, refused)):
            if not os.path.exists(path):
                sys.exit(f'{path} does not exist')
            have = [dict(h) for h in csv.DictReader(open(path))]
            if have != [{k: ('' if v is None else str(v)) for k, v in r.items()}
                        for r in want]:
                sys.exit(f'{path} is stale -- re-run '
                         f'scripts/extract_capital_plans.py')
        print(f'{OUT}: {len(rows)} rows, {len(refused)} refused, reproduces')
        return

    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(REFUSED, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=REFUSED_FIELDS)
        w.writeheader()
        w.writerows(refused)

    by = collections.defaultdict(list)
    for r in rows:
        by[(r['edition'], r['page'])].append(r)
    for r in refused:
        print(f'!! {r["edition"]} p{int(r["page"]):>3} REFUSED, not filed as a reading  '
              f'{r["reconciliation"][:110]}')
    for (ed, p), rs in sorted(by.items(), key=lambda kv: (kv[0][0], int(kv[0][1]))):
        mark = '  ' if rs[0]['status'] == 'checked' else '!!'
        n = sum(1 for r in rs if r['project'])
        print(f'{mark} {ed} p{int(p):>3} {rs[0]["copy"]:<22} plan FY{rs[0]["plan_fiscal_year"]}  '
              f'{n:>2} projects  {rs[0]["reconciliation"][:110]}')
    print()
    for line in compare_copies(rows):
        print(line)
    print(f'\nwrote {OUT}: {len(rows)} rows')
    print(f'wrote {REFUSED}: {len(refused)} pages refused')


def compare_copies(rows):
    """The Committee's list against the one printed in the town meeting article."""
    by = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in rows:
        if r['project'] and r['cost'] != '':
            by[r['edition']][r['copy']] += float(r['cost'])
    out = []
    for ed in sorted(by):
        copies = by[ed]
        if len(copies) < 2:
            continue
        vals = sorted(copies.items())
        same = abs(vals[0][1] - vals[1][1]) < 1
        out.append(f'{ed}: ' + ' ; '.join(f'{k} {v:,.2f}' for k, v in vals)
                   + (' -- the same plan' if same else ' -- DIFFERENT'))
    return out or ['no edition prints the plan twice in a form both copies could be read']


if __name__ == '__main__':
    main()
