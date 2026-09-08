"""Three published figures for what each sport costs, and the spread between them.

WHY THIS MODULE EXISTS. `athletics.py` carries two cost columns per sport as typed
constants, `cost` and `deckCost`, and its docstring has said since it was written that
the district has not reconciled them. Nothing computed the size of that disagreement and
nothing put it in front of a reader choosing which team to give up. This does both, and
it adds a THIRD column that is derived rather than typed.

THE THREE COLUMNS, and which of them rule 2 lets us derive:

  `cost`        "Athletic Program Costs by Sport", published with the FY26 budget
                materials. TRANSCRIBED. We hold the document; nothing in this repository
                is a machine-readable extract of it, so the 25 figures stay constants in
                `athletics.py`. Rule 2 asks that a figure be derived where it can be and
                that the reason be written down where it cannot. This is the reason.
  `deckCost`    "Cost of Running Each Sport", the Athletic Program Funding Overview deck
                of 5/1/2024. TRANSCRIBED, same reason.
  workbook      `Total Expenses` per sport per year in the district's own by-sport
                workbook, obtained from the Town by records request on 17 June 2026 and
                extracted to `sources/data/athletics-by-sport.csv` with the spreadsheet
                cell beside every value. DERIVED, here, at export time.

WHAT THIS ESTABLISHES. Three documents produced by the same district state three
different figures for what the same sport cost in the same year, and nothing published
reconciles them. That is a measurement, and it is the whole of what this module claims.

WHAT IT DOES NOT ESTABLISH. Which one is right, or even that all three are answering the
same question -- a programmatic cost, an all-in cost and a season's booked expenses would
legitimately differ, and no document here says which each column is. Rule 7: the
disagreement is the fact; an explanation for it would be a hypothesis.

FAIL CLOSED. A name crosswalk that matches nothing looks exactly like a district that
publishes nothing, so this refuses to produce a column at all unless every sport in the
roster resolves, every workbook row is either mapped or named in EXCLUDED, and the mapped
plus excluded rows add back to the column's own sum.
"""

import csv
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_CSV = os.path.join(os.path.dirname(_HERE), 'sources', 'data', 'athletics-by-sport.csv')

#: The workbook names its teams by season sheet and the FY26 planning roster does not, so
#: the two have to be crosswalked by hand. Each entry is (level, workbook sport name);
#: several roster entries are one team in the roster and two in the workbook, because the
#: workbook budgets boys and girls separately.
CROSSWALK = {
    'Football':             [('HS', 'Football')],
    'Cheer':                [('HS', 'Cheer')],
    'Field Hockey':         [('HS', 'Field Hockey')],
    'Cross Country':        [('HS', 'Boys CC'), ('HS', 'Girls CC')],
    'Golf':                 [('HS', 'Golf')],
    "Boys' Soccer":         [('HS', 'Boys Soccer')],
    "Girls' Soccer":        [('HS', 'Girls Soccer')],
    'Unified Basketball':   [('HS', 'Unified Basketball $100')],
    'Softball':             [('HS', 'Softball')],
    "Girls' Lacrosse":      [('HS', 'Girls Lax')],
    "Boys' Lacrosse":       [('HS', 'Boys Lax')],
    'Baseball':             [('HS', 'Baseball')],
    'Outdoor Track':        [('HS', 'Boys Track'), ('HS', 'Girls Track')],
    'Indoor Track':         [('HS', 'Indoor Track - Boys'), ('HS', 'Indoor Track - Girls')],
    'Unified Track':        [('HS', 'Unified Track ($100)')],
    "Girls' Basketball":    [('HS', 'HS Basketball - Girls')],
    "Boys' Basketball":     [('HS', 'HS BasketBall - Boys')],
    "Boys' Ice Hockey":     [('HS', 'Ice Hockey - Boys')],
    "Girls' Ice Hockey":    [('HS', 'Ice Hockey - Girls')],
    'Alpine Skiing':        [('HS', 'Ski Team')],
    'MS Cross Country':     [('MS', 'Cross Country')],
    'MS Field Hockey':      [('MS', 'Field Hockey')],
    'MS Track':             [('MS', 'Track')],
    "MS Girls' Basketball": [('MS', 'Basketball - Girls')],
    "MS Boys' Basketball":  [('MS', 'Basketball - Boys')],
}

#: Workbook rows that carry a Total Expenses figure and deliberately have no roster
#: counterpart. Both are stated rather than dropped, because a row silently discarded is
#: the difference between a column that ties and one that only looks as though it does.
EXCLUDED = {
    ('HS', 'Out of District'):
        'Out-of-district athletes, not a team. $0 in both years the workbook covers.',
    ('MS', 'Softball'):
        'A middle school team the workbook budgets and the FY26 planning roster does not '
        'list, so there is no sport here to attach it to.',
}

METRIC = 'Total Expenses'
SOURCE = ('athletics-by-sport-fy24-fy26.xlsx, obtained from the Town by records request, '
          '17 June 2026. Extracted to sources/data/athletics-by-sport.csv, which carries '
          'the spreadsheet cell beside every value.')


#: The workbook's own notes column, quoted verbatim. Not a cost column -- a column headed
#: `Costs for all 3 Seasons` in which the district works out how to divide district-wide
#: items across the three seasons. It is the reason a per-sport figure is not a per-sport
#: cost: MIAA membership, the league assessment, trainer supplies, CPR certification and
#: the Final Forms subscription are all divided by three and pushed into season totals.
#: Rule 13 -- these are the raw cell values, not our rendering of them.
SHARED_NOTE_METRIC = 'Costs for all 3 Seasons'


def shared_allocations(fy=2024):
    """Every note in the workbook's own `Costs for all 3 Seasons` column, verbatim."""
    out = []
    with open(_CSV, newline='') as fh:
        for r in csv.DictReader(fh):
            if r['metric'] != SHARED_NOTE_METRIC or int(r['fy']) != fy:
                continue
            out.append(dict(note=r['raw'], cell=r['cell'], season=r['season']))
    if not out:
        raise ValueError(f'no `{SHARED_NOTE_METRIC}` notes for FY{fy}')
    seen, uniq = set(), []
    for r in out:
        if r['note'] in seen:
            continue
        seen.add(r['note'])
        uniq.append(r)
    return uniq


def _rows():
    with open(_CSV, newline='') as fh:
        for r in csv.DictReader(fh):
            if r['metric'] != METRIC or r['is_numeric'] != '1':
                continue
            yield r


def workbook_costs(sports):
    """`Total Expenses` per roster sport per fiscal year, from the workbook extract.

    Returns ``{fy: {sport_name: (amount, [cells])}}``. Raises rather than returning a
    partial column: a crosswalk that stops matching must break the build, not quietly
    publish a zero.
    """
    by_year = {}
    for r in _rows():
        fy = int(r['fy'])
        by_year.setdefault(fy, {}).setdefault((r['level'], r['sport']), []).append(r)

    names = [s['name'] for s in sports]
    missing = [n for n in names if n not in CROSSWALK]
    if missing:
        raise ValueError(f'no workbook crosswalk for {missing}')

    out = {}
    for fy, rows in sorted(by_year.items()):
        column_sum = round(sum(float(r['value']) for rs in rows.values() for r in rs), 2)
        got, seen, cells = {}, set(), {}
        for name in names:
            keys = [k for k in CROSSWALK[name] if k in rows]
            if not keys:
                continue
            got[name] = round(sum(float(r['value']) for k in keys for r in rows[k]), 2)
            cells[name] = sorted(r['cell'] for k in keys for r in rows[k])
            seen.update(keys)
        unaccounted = [k for k in rows if k not in seen and k not in EXCLUDED]
        if unaccounted:
            raise ValueError(f'FY{fy}: workbook rows matched no sport and are not '
                             f'excluded: {unaccounted}')
        # The mapped rows plus the excluded rows must add back to the column the workbook
        # itself prints, or something was dropped on the way through.
        excluded_sum = round(sum(float(r['value'])
                                 for k in rows if k in EXCLUDED for r in rows[k]), 2)
        if abs(sum(got.values()) + excluded_sum - column_sum) > 0.02:
            raise ValueError(f'FY{fy}: mapped {sum(got.values()):,.2f} + excluded '
                             f'{excluded_sum:,.2f} does not tie to the column sum '
                             f'{column_sum:,.2f}')
        out[fy] = dict(
            bySport={n: dict(amount=v, cells=cells[n]) for n, v in got.items()},
            mapped=round(sum(got.values()), 2),
            excluded=excluded_sum,
            columnSum=column_sum,
            covered=len(got), roster=len(names))
    if not out:
        raise ValueError('no workbook Total Expenses rows found at all')
    return out


#: The year all three columns are about. `cost` and `deckCost` are both FY24-basis
#: documents, so this is the only year a three-way comparison is like for like.
COMPARISON_FY = 2024


def export(sports):
    """Every sport with its three published costs, and the spread between them.

    Nothing here rounds a spread into a claim about which figure is right. The columns are
    reported, the difference is computed, and the page says the district has not
    reconciled them.
    """
    wb = workbook_costs(sports)
    if COMPARISON_FY not in wb:
        raise ValueError(f'the workbook extract has no FY{COMPARISON_FY} column, which is '
                         'the only year all three sources describe')
    base = wb[COMPARISON_FY]['bySport']

    rows = []
    for s in sports:
        w = base.get(s['name'])
        cols = dict(costsBySport=s['cost'], deck=s['deckCost'])
        if w:
            cols['workbook'] = w['amount']
        vals = [v for v in cols.values() if v is not None]
        lo, hi = min(vals), max(vals)
        rows.append(dict(
            name=s['name'], level=s['level'], students=s['students'],
            columns=cols,
            cells=w['cells'] if w else [],
            low=round(lo, 2), high=round(hi, 2), spread=round(hi - lo, 2),
            spreadPct=round((hi - lo) / lo * 100, 1) if lo else None,
        ))

    def col(key):
        return round(sum(r['columns'][key] for r in rows if key in r['columns']), 2)

    totals = dict(costsBySport=col('costsBySport'), deck=col('deck'),
                  workbook=col('workbook'))
    lo_t, hi_t = min(totals.values()), max(totals.values())

    return dict(
        fy=COMPARISON_FY,
        sports=rows,
        totals=totals,
        totalLow=lo_t, totalHigh=hi_t,
        totalSpread=round(hi_t - lo_t, 2),
        totalSpreadPct=round((hi_t - lo_t) / lo_t * 100, 1),
        widest=max(rows, key=lambda r: r['spreadPct'] or 0)['name'],
        widestPct=max(r['spreadPct'] or 0 for r in rows),
        agreeing=sum(1 for r in rows if r['spread'] < 0.005),
        count=len(rows),
        # The workbook column for the following year, kept SEPARATE rather than blended
        # in: it is a different fiscal year and the other two columns do not have one.
        workbookYears={fy: dict(total=v['mapped'], covered=v['covered'],
                                columnSum=v['columnSum'], excluded=v['excluded'])
                       for fy, v in wb.items() if v['covered'] == len(sports)},
        columnMeaning=dict(
            costsBySport='"Athletic Program Costs by Sport", published with the FY26 '
                         'budget materials. FY24 programmatic cost per sport.',
            deck='"Cost of Running Each Sport", Athletic Program Funding Overview deck, '
                 '1 May 2024.',
            workbook='`Total Expenses` per sport in the district’s own by-sport '
                     'workbook. ' + SOURCE,
        ),
        derivedColumn='workbook',
        source=SOURCE,
        sharedNotes=shared_allocations(COMPARISON_FY),
        sharedNoteColumn=SHARED_NOTE_METRIC,
        excluded=[dict(level=lvl, sport=name, why=why)
                  for (lvl, name), why in EXCLUDED.items()],
    )


if __name__ == '__main__':
    import sys
    sys.path.insert(0, _HERE)
    from athletics import SPORTS
    e = export(SPORTS)
    print(f"FY{e['fy']}, {e['count']} sports")
    for k, v in e['totals'].items():
        print(f"  {k:<14} {v:>14,.2f}")
    print(f"  spread {e['totalSpread']:,.2f} ({e['totalSpreadPct']}%)")
    print(f"  widest per sport: {e['widest']} {e['widestPct']}%")
    for r in sorted(e['sports'], key=lambda r: -(r['spreadPct'] or 0))[:8]:
        print(f"  {r['name']:<22} {r['low']:>10,.2f} .. {r['high']:>10,.2f}  "
              f"{r['spreadPct']:>8.1f}%")
    print(' workbook by year:', e['workbookYears'])
