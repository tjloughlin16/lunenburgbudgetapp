"""How the town's capital programme is paid for, and how much of it is free cash.

Free cash is not idle money. It is the capital programme's largest and steadiest funding
source, and any dollar redirected out of it is a dollar the capital plan has to find
somewhere else or go without. A page that says "$794,872 could go to the schools without
breaching the guideline" and stops there has told half the story.

The source is the FY27 capital plan, Article 13, page 8: `Historical Capital Program
Funding`, a ten-year table with one row per fiscal year and one column per funding source.
Page 9 gives the FY2027 plan itself.

**Reconciled to a total the source prints.** Each row states a total and then its parts, and
this checks the parts sum to it before writing. Two of the ten rows are dropped rather than
guessed at: FY19 and FY20 carry a fifth figure with a footnote marker attached (`*` a
transfer from the Premium Reserved for Capital fund, `**` five-year borrowing for a ladder
truck), and the extraction cannot tell reliably which column a footnoted number belongs to.
Dropping two rows and saying so is better than eight clean rows and two invented ones.

    python3 scripts/extract_capital_plan.py

It also extracts the FY27 programme itself, which the town publishes as a RANKED list with
a running total — CPC rank, department, project, cost, cumulative cost. That ranking is the
Capital Planning Committee's, not ours, which is what makes it usable: "redirect $X of free
cash" maps onto the items that fall off the bottom without anybody here choosing which
projects matter.

Writes sources/data/capital-funding-history.csv and sources/data/capital-plan-fy27.csv
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'txt', 'town-article13-fy27-capital-plan.txt')
OUT = os.path.join(ROOT, 'sources', 'data', 'capital-funding-history.csv')

# The column order printed on page 8, once the wrapped header is read in order.
COLUMNS = ['free_cash', 'taxation', 'unexpended_prior_year_capital', 'other']


def main():
    if not os.path.exists(SRC):
        sys.exit(f'missing {SRC}')
    txt = open(SRC, encoding='utf-8', errors='ignore').read()

    rows, skipped = [], []
    for fy, tail in re.findall(r'^(FY\d{2}) Capital Plan ([^\n]+)$', txt, re.M):
        nums = [float(x.replace('$', '').replace(',', ''))
                for x in re.findall(r'\$[\d,]+\.\d\d', tail)]
        if len(nums) < 2:
            skipped.append((fy, 'no figures parsed'))
            continue
        total, parts = nums[0], nums[1:]
        if re.search(r'\*', tail):
            skipped.append((fy, 'footnoted figure — column assignment not reliable'))
            continue
        if abs(total - sum(parts)) > 0.01:
            sys.exit(f'{fy}: parts sum to {sum(parts):,.2f}, the row prints {total:,.2f}. '
                     'Refusing to write.')
        row = dict(fy=2000 + int(fy[2:]), total=f'{total:.2f}')
        for i, name in enumerate(COLUMNS):
            row[name] = f'{parts[i]:.2f}' if i < len(parts) else '0.00'
        rows.append(row)

    if not rows:
        sys.exit('parsed no capital rows; the table layout has changed')

    # The FY2027 plan, from page 9.
    m = re.search(r'FY2027 Capital Program Funding.*?Free Cash \$([\d,]+)', txt, re.S)
    planned = float(m.group(1).replace(',', '')) if m else None
    # And the document's own average row, as a check on ours.
    ma = re.search(r'^Average ([^\n]+)$', txt, re.M)
    stated_avg = None
    if ma:
        a = [float(x.replace('$', '').replace(',', ''))
             for x in re.findall(r'\$[\d,]+\.\d\d', ma.group(1))]
        stated_avg = dict(total=a[0], free_cash=a[1]) if len(a) > 1 else None

    # The ranked programme. Each line ends with cost then cumulative cost, and the
    # cumulative column is the source's own running total -- so it is checked rather than
    # recomputed, and a mismatch means the parse has gone wrong.
    #
    # Scoped to the FY27 programme's own section. The document contains more than one table
    # of similarly-shaped lines, and matching across the whole file pulled rows from
    # another one -- caught immediately, because the running total came out at $3,617,208
    # against a printed cumulative of $350,000 on the very first item.
    # The FULL CPC ranking, not the funded subset. The document prints both: 22 projects
    # ranked and costed, of which the first 12 are funded. The queue is the useful list --
    # $1,437,005 of ranked work is already below the line before anybody touches free cash,
    # which is what makes a dollar removed a dollar of requested work not done.
    sec = re.search(r'CPC Rankings\s*\n.*?CPC Rank.*?\n(.*?)\n[\d,]+\s*\n', txt, re.S)
    section = sec.group(1) if sec else ''
    items, running = [], 0.0
    for rank, dept, name, cost, cum in re.findall(
            r'^(\d{1,2}) (DPW|Police|Fire|Schools|Facilities|IT) (.+?) '
            r'([\d,]+) ([\d,]+)$', section, re.M):
        c = float(cost.replace(',', ''))
        running += c
        stated = float(cum.replace(',', ''))
        if abs(running - stated) > 0.01:
            sys.exit(f'capital item {rank}: running total {running:,.0f} does not match the '
                     f'printed cumulative {stated:,.0f}. Refusing to write.')
        items.append(dict(rank=int(rank), dept=dept, project=name.strip(),
                          cost=f'{c:.2f}', cumulative=f'{stated:.2f}',
                          # The town funds down to $1,830,203; everything after that is
                          # ranked, costed and unfunded.
                          funded='yes' if stated <= 1_830_203 else 'no'))
    if items:
        out2 = os.path.join(ROOT, 'sources', 'data', 'capital-plan-fy27.csv')
        with open(out2, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=['rank', 'dept', 'project', 'cost',
                                               'cumulative', 'funded'])
            w.writeheader()
            w.writerows(items)

    rows.sort(key=lambda r: r['fy'])
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'total'] + COLUMNS)
        w.writeheader()
        w.writerows(rows)

    fc = [float(r['free_cash']) for r in rows]
    print(f'wrote {os.path.relpath(OUT, ROOT)}  ({len(rows)} years, each reconciled to the '
          'total its own row prints)\n')
    print(f"  {'FY':<6}{'capital total':>15}{'from free cash':>16}{'share':>8}")
    for r in rows:
        t, f = float(r['total']), float(r['free_cash'])
        print(f"  {r['fy']:<6}{t:>15,.0f}{f:>16,.0f}{f / t * 100:>7.0f}%")
    print(f"\n  free cash into capital, mean of these {len(fc)} years: ${sum(fc) / len(fc):,.0f}")
    if stated_avg:
        print(f"  the document's own ten-year average           : "
              f"${stated_avg['free_cash']:,.0f} of ${stated_avg['total']:,.0f}")
        print('  (ours differs because two footnoted rows are excluded — see the docstring)')
    if planned:
        print(f"\n  FY2027 capital programme plans to draw ${planned:,.0f} from free cash.")
    if items:
        print(f"\n  the FY27 programme, ranked by the Capital Planning Committee "
              f"({len(items)} projects, ${float(items[-1]['cumulative']):,.0f}):")
        for it in items:
            mark = ' ' if it['funded'] == 'yes' else '·'
            print(f"  {mark} {it['rank']:>2}. {it['dept']:<11}{it['project'][:46]:<48}"
                  f"${float(it['cost']):>9,.0f}")
        unf = sum(float(i['cost']) for i in items if i['funded'] == 'no')
        print(f"\n    · = ranked and requested but NOT funded: ${unf:,.0f} across "
              f"{sum(1 for i in items if i['funded'] == 'no')} projects")

    if skipped:
        print('\n  rows deliberately not extracted:')
        for fy, why in skipped:
            print(f'    {fy}: {why}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
