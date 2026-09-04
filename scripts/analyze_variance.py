"""Budget against actual, across every line, every group and every year.

Written after a first attempt ranked groups by pooled dollar variance, looked at the top
six, and called it a sweep. Pooling hides exactly what this data is full of: a group whose
overspends and underspends cancel reads as quiet when nothing inside it is.

So this reports EVERY group, not a ranking. It reports each year, not a pool. It measures
four different things, because each hides something the others show:

  net       the pooled variance -- what a treasurer feels
  gross     over and under added as absolutes -- what a budget officer feels
  churn     gross divided by net; high means the group cancels itself out
  spread    worst year to best year

And it states coverage everywhere. A group measured in two years is not a finding.

    python3 scripts/analyze_variance.py            # the whole thing
    python3 scripts/analyze_variance.py --lines    # add the line-level detail
"""
import os, sys, csv, collections, statistics as st, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources/data')
_sp = importlib.util.spec_from_file_location(
    'elh', os.path.join(ROOT, 'scripts/extract_line_history.py'))
elh = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(elh)

# FY21's "actual" column is its budget in 117 of 120 lines -- the books were not closed.
EXCLUDED_YEARS = {2021}


def load():
    wb = [r for r in csv.DictReader(open(os.path.join(DATA, 'lps-budget-lines.csv')))
          if r['kind'] == 'line']
    fn = {elh.norm(r['line_item']): (r['function_group'] or '').strip() for r in wb}
    sec = {elh.norm(r['line_item']): r['section'] for r in wb}
    label = {elh.norm(r['line_item']): r['line_item'].strip() for r in wb}
    cell = collections.defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(DATA, 'line-history.csv'))):
        # variant='' only -- a scenario column is a different proposal for the same year,
        # not another reading of the same figure. See notes/SCHEMA.md, budget_figure.
        if r.get('variant'):
            continue
        cell[(r['key'], int(r['fy']))][r['stage']] = (float(r['value']),
                                                      r['documents_disagree'] == '1')
        label.setdefault(r['key'], r['label'].strip())
    return wb, fn, sec, label, cell


# A YEAR IS NOT A MEASUREMENT UNTIL ENOUGH OF IT IS MEASURED. FY2016 and FY2017 each
# resolve four usable lines -- out of roughly three hundred and fifty -- because one small
# FY19 department document happens to print those columns for a handful of technology
# lines. Four lines is not a budget, and a table that shows `FY16 +0.00%` beside `FY23
# +0.54%` invites a reader to weigh them the same. Twenty is the floor, stated here rather
# than left to whoever reads the table.
MIN_LINES_PER_YEAR = 20


def thin_years(recs):
    """{fy: n} for years with too few usable lines to read, reported rather than hidden."""
    n = collections.Counter(fy for _, fy, _, _ in recs)
    return {fy: c for fy, c in n.items() if c < MIN_LINES_PER_YEAR}


def usable(fy, b, a):
    """A cell fit to compare, and the reasons one is not -- each stated, none silent."""
    if fy in EXCLUDED_YEARS:
        return 'FY21 excluded'
    if not b or not a:
        return 'missing one side'
    if b[1] or a[1]:
        return 'documents disagree'
    if b[0] < 10_000:
        return 'budget under $10k'
    if a[0] < 1_000 or not (0.02 <= a[0] / b[0] <= 20):
        return 'implausible ratio — parse artifact'
    return None


def main():
    wb, fn, sec, label, cell = load()
    recs, dropped = [], collections.Counter()
    for (k, fy), v in cell.items():
        why = usable(fy, v.get('settled'), v.get('actual'))
        if why:
            if v.get('settled') or v.get('actual'):
                dropped[why] += 1
            continue
        recs.append((k, fy, v['settled'][0], v['actual'][0]))

    thin = thin_years(recs)
    for fy, n in sorted(thin.items()):
        dropped[f'FY{fy % 100}: only {n} usable lines'] += n
    recs = [r for r in recs if r[1] not in thin]

    print('=' * 78)
    print('COVERAGE — what is being measured, and what is not')
    print('=' * 78)
    yrs = sorted({fy for _, fy, _, _ in recs})
    print(f'  {len(recs)} usable line-years across FY{yrs[0]%100}–FY{yrs[-1]%100}')
    print(f'  {len({k for k,_,_,_ in recs})} distinct lines')
    per = collections.Counter(fy for _, fy, _, _ in recs)
    print('  by year: ' + ', '.join(f'FY{y%100} {per[y]}' for y in yrs))
    print(f'\n  {sum(dropped.values())} line-years excluded, and why:')
    for why, n in dropped.most_common():
        print(f'     {n:>5}  {why}')
    lines_wb = {elh.norm(r['line_item']) for r in wb}
    seen = {k for k, _, _, _ in recs}
    print(f'\n  {len(lines_wb - seen)} lines in the FY27 workbook never measured here')
    print(f'  {len(seen - lines_wb)} lines measured that the workbook does not carry '
          f'(retired lines)')

    grp = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))
    for k, fy, b, a in recs:
        g = fn.get(k) or '(unmapped)'
        grp[g][fy][0] += b
        grp[g][fy][1] += a

    print('\n' + '=' * 78)
    print('EVERY FUNCTION GROUP — all of them, no ranking, no cutoff')
    print('=' * 78)
    print(f"{'group':<42}{'yrs':>4}{'budget':>12}{'net':>10}{'gross':>10}"
          f"{'churn':>7}{'spread':>16}")
    rows = []
    for g, years in grp.items():
        ys = sorted(years)
        b = sum(years[y][0] for y in ys)
        a = sum(years[y][1] for y in ys)
        devs = [years[y][1] / years[y][0] - 1 for y in ys if years[y][0]]
        gross = sum(abs(years[y][1] - years[y][0]) for y in ys)
        net = a - b
        rows.append(dict(g=g, n=len(ys), b=b, net=net, gross=gross,
                         churn=(gross / abs(net)) if abs(net) > 1 else float('inf'),
                         lo=min(devs) if devs else 0, hi=max(devs) if devs else 0,
                         devs=devs, years=years))
    for r in sorted(rows, key=lambda x: -x['b']):
        ch = '—' if r['churn'] == float('inf') else f"{r['churn']:.1f}x"
        print(f"  {r['g'][:40]:<42}{r['n']:>4}{r['b']:>12,.0f}{r['net']:>+10,.0f}"
              f"{r['gross']:>10,.0f}{ch:>7}"
              f"{r['lo']*100:>+8.0f}%{r['hi']*100:>+7.0f}%")
    # ---------------------------------------------------------------- churn
    print('\n' + '=' * 78)
    print('GROUPS THAT CANCEL THEMSELVES OUT — a quiet net over a loud inside')
    print('=' * 78)
    print('  Churn is gross variance over net. 1.0 means every year misses the same way.')
    print('  High churn means the group looks calm only because its years offset.\n')
    print(f"{'group':<42}{'net':>10}{'gross':>10}{'churn':>8}   by year")
    for r in sorted(rows, key=lambda x: -x['churn']):
        if r['n'] < 3 or r['gross'] < 20_000:
            continue
        ys = sorted(r['years'])
        cells = ' '.join(f"{(r['years'][y][1]/r['years'][y][0]-1)*100:+.0f}%" for y in ys)
        ch = 'inf' if r['churn'] == float('inf') else f"{r['churn']:.1f}x"
        print(f"  {r['g'][:40]:<42}{r['net']:>+10,.0f}{r['gross']:>10,.0f}{ch:>8}   {cells}")

    # ------------------------------------------------------- direction & drift
    print('\n' + '=' * 78)
    print('DIRECTION — groups that always miss the same way, and groups that drift')
    print('=' * 78)
    always_over, always_under, drifting = [], [], []
    for r in rows:
        if r['n'] < 4:
            continue
        d = r['devs']
        if all(x > 0.02 for x in d):
            always_over.append(r)
        elif all(x < -0.02 for x in d):
            always_under.append(r)
        ys = sorted(r['years'])
        if len(ys) >= 4:
            first = st.mean(d[:2]); last = st.mean(d[-2:])
            if abs(last - first) > 0.05:
                drifting.append((last - first, r))
    print(f'\n  Over in every measured year ({len(always_over)}):')
    for r in sorted(always_over, key=lambda x: -x['net']):
        print(f"     {r['net']:>+10,.0f}  {r['g'][:44]:<46} {r['n']} yrs")
    print(f'\n  Under in every measured year ({len(always_under)}):')
    for r in sorted(always_under, key=lambda x: x['net']):
        print(f"     {r['net']:>+10,.0f}  {r['g'][:44]:<46} {r['n']} yrs")
    print(f'\n  Drifting — first two years against last two ({len(drifting)}):')
    for delta, r in sorted(drifting, key=lambda x: -abs(x[0])):
        d = r['devs']
        print(f"     {delta*100:>+7.0f}pts  {r['g'][:40]:<42} "
              f"{st.mean(d[:2])*100:+.0f}% -> {st.mean(d[-2:])*100:+.0f}%")

    # ------------------------------------------------------------- by year
    print('\n' + '=' * 78)
    print('BY YEAR — the whole measured budget')
    print('=' * 78)
    byyr = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for k, fy, b, a in recs:
        byyr[fy][0] += b; byyr[fy][1] += a; byyr[fy][2] += 1
    print(f"{'FY':<6}{'lines':>7}{'budgeted':>14}{'spent':>14}{'net':>12}{'':>8}")
    for fy in sorted(byyr):
        b, a, n = byyr[fy]
        print(f'FY{fy%100:<4}{n:>7}{b:>14,.0f}{a:>14,.0f}{a-b:>+12,.0f}{(a/b-1)*100:>+7.2f}%')

    # ------------------------------------------------------------ the lines
    print('\n' + '=' * 78)
    print('INDIVIDUAL LINES — biggest movers, and the steadiest missers')
    print('=' * 78)
    per = collections.defaultdict(list)
    for k, fy, b, a in recs:
        per[k].append((fy, b, a, a / b - 1))
    net = [(sum(a - b for _, b, a, _ in v), k, v) for k, v in per.items()]
    print('\n  Ten largest overspends by dollars:')
    for nv, k, v in sorted(net, reverse=True)[:10]:
        print(f"     {nv:>+11,.0f}  {label.get(k,k)[:40]:<42} {len(v)} yrs  "
              + ' '.join(f'{d*100:+.0f}%' for _, _, _, d in sorted(v)))
    print('\n  Ten largest underspends by dollars:')
    for nv, k, v in sorted(net)[:10]:
        print(f"     {nv:>+11,.0f}  {label.get(k,k)[:40]:<42} {len(v)} yrs  "
              + ' '.join(f'{d*100:+.0f}%' for _, _, _, d in sorted(v)))
    steady = [(st.mean([d for _, _, _, d in v]), k, v) for k, v in per.items()
              if len(v) >= 4 and (all(d > 0.02 for _, _, _, d in v)
                                  or all(d < -0.02 for _, _, _, d in v))]
    print(f'\n  Lines missing the same way in every measured year ({len(steady)}):')
    for mn, k, v in sorted(steady, key=lambda x: -abs(x[0])):
        dollars = st.mean([a - b for _, b, a, _ in v])
        print(f"     {mn*100:>+7.0f}%  {dollars:>+10,.0f}/yr  {label.get(k,k)[:42]:<44} "
              f"{len(v)} yrs")
    return rows, recs, label, fn, sec


def write_csv(rows):
    """The sweep as data, so a reader can rank it their own way rather than mine."""
    out = os.path.join(DATA, 'variance-by-group.csv')
    with open(out, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['function_group', 'years', 'budgeted', 'spent', 'net', 'gross',
                    'churn', 'worst_year', 'best_year'])
        for r in sorted(rows, key=lambda x: -x['b']):
            w.writerow([r['g'], r['n'], f"{r['b']:.0f}", f"{r['b']+r['net']:.0f}",
                        f"{r['net']:.0f}", f"{r['gross']:.0f}",
                        '' if r['churn'] == float('inf') else f"{r['churn']:.2f}",
                        f"{r['lo']:.4f}", f"{r['hi']:.4f}"])
    print(f'\nwrote {out}')


if __name__ == '__main__':
    rows, *_ = main()
    write_csv(rows)
