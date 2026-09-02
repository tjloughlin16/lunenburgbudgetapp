"""Write the outstanding data request, computed from what the archive actually holds.

    python3 scripts/build_request_doc.py

Writes `notes/DATA-REQUEST.md`.

Generated rather than maintained, for the reason everything else here is: a hand-written
request list goes stale the moment something arrives, and the failure mode is asking a
public official twice for a document they already sent. That is a real cost -- it spends
goodwill that the next request needs.

So this reads the coverage matrix out of the database, prints only what is genuinely
missing, and marks anything received since the last run. Re-run it after every ingest.
"""
import json
import os
import sqlite3
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
LEDGER = os.path.join(ROOT, 'fy28', 'public', 'data', 'ledger.json')
OUT = os.path.join(ROOT, 'notes', 'DATA-REQUEST.md')

# The years worth asking for. FY24 and FY25 are closed; FY26 is closing now. Anything
# earlier is a nice-to-have and should not crowd out the three that matter.
YEARS = [2024, 2025, 2026]

# One canonical description of the report, so the parameters cannot drift between the
# letter, the page and this file.
GLYTDBUD = (
    'MUNIS **YEAR-TO-DATE BUDGET REPORT**, program `glytdbud`, run with '
    '**Print totals only: N** and **Suppress zero balance accounts: N**'
)


def main():
    if not os.path.exists(LEDGER):
        print('run scripts/export_ledger.py first')
        return 1
    cov = json.load(open(LEDGER, encoding='utf-8'))['coverage']
    defs = {r['id']: r for r in cov['rowDefs']}
    cells = cov['cells']

    def state(fy, rid):
        return (cells.get(str(fy), {}).get(rid) or {}).get('state', 'missing')

    # Only the rows the Town can actually produce. The district's own budget documents
    # are somebody else's ask and do not belong in a letter to the Town Manager.
    town_rows = [r for r in cov['rowDefs'] if r['effort'] == 'records request']

    have, need = [], []
    for rd in town_rows:
        for fy in YEARS:
            st = state(fy, rd['id'])
            (have if st == 'obtained' else need).append((fy, rd, st))

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    funds = [dict(r) for r in db.execute(
        """SELECT fa.fund, f.name FROM fund_activity fa
           LEFT JOIN fund f ON f.fund = fa.fund
           WHERE (fa.salaries + fa.expenditure) > 0
           ORDER BY (fa.salaries + fa.expenditure) DESC LIMIT 12""")]

    L = []
    w = L.append
    w('# What we still need from the Town')
    w('')
    w(f'Generated {date.today().isoformat()} by `scripts/build_request_doc.py` from the '
      'coverage matrix in the database. **Re-run it before sending anything** — asking '
      'twice for a document already sent spends goodwill the next request needs.')
    w('')
    w(f'**{len(need)} of {len(need) + len(have)}** report-years outstanding for '
      f'FY{YEARS[0]}–FY{YEARS[-1]}.')
    w('')
    w('---')
    w('')

    # ---- the ask, in the order it should be asked -----------------------------------
    w('## 1. The one that unlocks the most')
    w('')
    w('**The same report for a Fund other than 0100** — the school grant, revolving and '
      'school choice funds.')
    w('')
    w('Everything received so far is Fund 0100: the town\'s share and nothing else. The '
      'district\'s budget is **net** — a line is what the town must raise after grants '
      'and fees have paid for part of the thing — so a line reading $20,000 can be a '
      '$220,000 line, and no document we hold marks which. These are the funds we know '
      'spent money on the schools in FY26 and cannot attach to any line:')
    w('')
    w('| fund | |')
    w('|---|---|')
    for f in funds:
        w(f"| `{f['fund']}` | {f['name'] or ''} |")
    w('')
    w('The simplest form of the ask: **the same report with the Fund criterion left '
      'blank**, which returns every fund at once. Failing that, the funds above.')
    w('')

    w('## 2. The one that makes a surplus computable at all')
    w('')
    w('**Period 13 — the year-end close.** We now hold FY26 at period 12, which is June '
      'with the books still open. Period 13 is after purchase orders are cleared in the '
      'lapse period, and that step is not cosmetic: it moved the FY25 school figure from '
      '$582,115.44 on 3 September 2025 to $603,885.97 on 17 September.')
    w('')
    w('Until a period 13 report exists for a year, that year\'s surplus cannot be '
      'computed here — only estimated from a report the Town Manager herself describes '
      'as "likely to continue to adjust".')
    w('')
    w('Alongside it: **the purchase orders closed against the year after its initial '
      'close**, with amounts and dates. That is not a standard report and has to be '
      'asked for in those words.')
    w('')

    w('## 3. The back years, in the same form')
    w('')
    w(f'{GLYTDBUD}.')
    w('')
    w('| fiscal year | period | what it is | status |')
    w('|---|---|---|---|')
    for fy, rd, st in sorted(need, key=lambda x: (x[0], x[1]['id'])):
        mark = {'missing': 'not held', 'partial': '**partial — see note**'}[st]
        w(f"| FY{fy} | {rd['label']} | {rd['why']} | {mark} |")
    w('')
    if have:
        w('### Already received — do not ask again')
        w('')
        for fy, rd, _ in sorted(have, key=lambda x: (x[0], x[1]['id'])):
            w(f'- FY{fy} — {rd["label"]}')
        w('')

    w('---')
    w('')
    w('## Why each one matters, in one line')
    w('')
    for rd in town_rows:
        w(f"- **{rd['label']}** — {rd['why']}")
    w('')
    w('## What is NOT being asked of the Town')
    w('')
    w('So the request stays as small as it honestly can be:')
    w('')
    w('- The district\'s own proposed and approved budget documents. Those are the '
      'district\'s to publish and several years are already mirrored here.')
    w('- DESE\'s figures. Those are a public download and already ingested.')
    w('- Anything before FY2024, unless it is free to include.')
    w('')
    w('## One document that is the district\'s, not the Town\'s')
    w('')
    w('**The End of Year Financial Report as submitted to DESE, all schedules, FY2024 '
      'and FY2025.** Schedule 1 separates revenues and expenditures *by source of funds*, '
      'which is exactly the question the netting problem asks. DESE does not publish it '
      'per district — that page is a submission portal — but Lunenburg files it, so '
      'Lunenburg holds a copy.')
    w('')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    print('  %d outstanding, %d already received' % (len(need), len(have)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
