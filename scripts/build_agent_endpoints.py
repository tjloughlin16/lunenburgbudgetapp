#!/usr/bin/env python3
"""Publish the data in a form an agent can read, and an llms.txt that explains it.

A resident who wants to check this site should not have to be a resident who can write a
scraper. Increasingly the way somebody checks a claim is to point an assistant at it, and
an assistant pointed at a React app gets a bundle of JavaScript.

So the same data the app runs on is published at stable addresses, with an llms.txt at the
root explaining what is there and -- more importantly -- how to not misuse it. The single
biggest risk is somebody computing a growth rate from a budget column to an actual column,
which is the exact error that cost us a week. The file says so, in the place a reader
looking for the data will see it.

Generated rather than written, so it cannot drift from what it describes.

    python3 scripts/build_agent_endpoints.py
"""
import csv
import json
import os
import shutil
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public')
DATA = os.path.join(PUB, 'data')
SITE = 'https://lunenburgbudgetproject.org'


def usd(n):
    return f'${round(n):,}'


def main():
    os.makedirs(DATA, exist_ok=True)
    model = json.load(open(os.path.join(ROOT, 'fy28', 'src', 'data', 'model.json')))
    sources = json.load(open(os.path.join(ROOT, 'fy28', 'src', 'data', 'sources.json')))

    # ---- the data itself, at addresses that will not move -------------------
    published = []
    for src, name, what in [
        (os.path.join(ROOT, 'fy28', 'src', 'data', 'model.json'), 'model.json',
         'Every figure the site computes: the FY27 base by bucket, the growth assumptions, '
         'the projection, the programme catalogue, the conclusions, and the citations.'),
        (os.path.join(ROOT, 'fy28', 'src', 'data', 'sources.json'), 'sources.json',
         'The document archive: every source, its group, its size, and the URL it is '
         'served from.'),
        (os.path.join(ROOT, 'sources', 'data', 'lps-budget-lines.csv'), 'budget-lines.csv',
         'The district budget, 351 line items, one column per fiscal year and scenario. '
         'The tidy form of the workbook everything else is derived from.'),
        (os.path.join(ROOT, 'sources', 'district-budget-page', 'index.csv'),
         'district-page-index.csv',
         'The 87 documents mirrored from the district budget page: label, our copy, the '
         'extracted text, the district’s original URL, and a sha256.'),
        (os.path.join(ROOT, 'sources', 'minutes', 'index.csv'), 'minutes-index.csv',
         'Every agenda and set of minutes the town publishes: board, date, kind, and the '
         'town’s own URL. 1,422 rows.'),
    ]:
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DATA, name))
            published.append((name, what, os.path.getsize(src)))

    a, f = model['assumptions'], model['fy27']
    gap = next(h for h in model['headlines'] if h['id'] == 'gap')
    counts = {}
    for g in sources['groups']:
        counts[g.get('section', 'other')] = counts.get(g.get('section', 'other'), 0) \
            + len(g['items'])

    lines = [
        '# Lunenburg Budget Project',
        '',
        '> An independent projection of the Lunenburg, Massachusetts school budget, built '
        'from documents the town and district published. Not affiliated with either. '
        'Every figure is traceable to a source in the archive below.',
        '',
        f'Data current as of {date.today().isoformat()}. Base year FY27. There is no FY28 '
        'budget yet; everything after FY27 is a projection.',
        '',
        '## Read this before computing anything',
        '',
        'The archive contains two kinds of number and they must never be mixed in one '
        'calculation:',
        '',
        '- **Budget columns** (`fy25_budget`, `fy26_final`, `fy27_level_service`, '
        '`fy27_balanced`) are what somebody voted or proposed.',
        '- **Actual columns** (`fy23_actual`, `fy24_actual`, `fy25_actual`, '
        '`fy26_actual_td`, `fy26_encumb_td`) are what was spent.',
        '',
        'They differ by up to 59% on some lines. A growth rate measured from an actual to '
        'a budget is partly growth and partly the step between the two, and produces a '
        'confident wrong answer. Every projection on this site uses budget columns only.',
        '',
        '`fy27_level_service` is the district’s own arithmetic for what the same '
        'services cost the following year. It is the correct endpoint for a cost-growth '
        'rate. `fy27_balanced` is what was actually adopted, and contains cuts, so a rate '
        'ending there measures policy rather than escalation.',
        '',
        '## The headline figures',
        '',
        f'- FY27 school appropriation: {usd(f["lps_appropriation"])} (the adopted '
        f'"Balanced" budget)',
        f'- Projected FY28 gap: {gap["value"]} — {gap["sub"]}',
        f'- Growth assumptions: salaries {a["salaries"]:.1%}, health insurance '
        f'{a["health"]:.1%}, special education {a.get("sped", 0):.1%}, out-of-district '
        f'tuition {a["sped_tuition"]:.1%}, transport {a["transport"]:.1%}, utilities '
        f'{a["utilities"]:.1%}, everything else {a["other"]:.1%}',
        f'- Levy growth: {a["levy_growth"]:.1%} (Proposition 2½, statutory)',
        '',
        'Only the special education rate is ours. The rest are the district’s own '
        'stated assumptions, a signed contract, or statute. `model.json` → `citations` '
        'says which is which for every headline figure.',
        '',
        '## Data',
        '',
    ]
    for name, what, size in published:
        lines.append(f'- [{name}]({SITE}/data/{name}) ({size / 1e6:.1f}MB): {what}')
    lines += [
        '',
        '## Documents',
        '',
        f'{sources["totals"]["documents"]} documents, each downloadable at '
        f'`{SITE}/docs/<path>`. `sources.json` lists every one with its path, size and '
        'group. Three sections, and the difference matters:',
        '',
        f'- **Published by the town, the district and the state** — '
        f'{counts.get("theirs", 0)} documents. Primary sources.',
        f'- **Held for reference, not used in the analysis** — '
        f'{counts.get("reference", 0)} documents, the district’s whole budget page '
        f'mirrored back to FY18. Nothing here feeds a figure on the site.',
        f'- **Written by this project** — {counts.get("ours", 0)} documents. Our '
        f'analyses and machine-readable extracts. These are arguments, not sources.',
        '',
        'Fifteen documents came from the Town by records request rather than off a '
        'website; they carry `byRequest` in `sources.json` and are the only ones recording '
        'money actually spent.',
        '',
        'Text has been extracted from nearly every document, including scans that had no '
        'text layer. Where a document has extracted text, `sources.json` gives a '
        '`textUrl`. Reading the text is usually faster than the PDF.',
        '',
        '## Meeting archive',
        '',
        f'{sources["corpus"]["fetched"]:,} agendas and sets of minutes across '
        f'{sources["corpus"]["boardCount"]} town boards, '
        f'{sources["corpus"]["from"]} to {sources["corpus"]["to"]}. The scanned originals '
        f'are not mirrored; [minutes-index.csv]({SITE}/data/minutes-index.csv) carries the '
        f'town’s own URL for each. Extracted text of all of them is in the repository.',
        '',
        '## What this site does not know',
        '',
        '- Out-of-district special education **placement counts** by year. Dollars cannot '
        'distinguish fewer children from a more honest estimate.',
        '- FY26 **year-end** figures. Everything held for FY26 stops at 31 March 2026.',
        '- Whether budgeted positions were **filled**. A budget line is an intention.',
        '',
        '## Provenance',
        '',
        'Source: https://github.com/tjloughlin16/lunenburgbudgetapp. Documents are served '
        'byte-identical to the archive; the build verifies this by hash. One file, a 53MB '
        'scan of the teachers’ agreement, is served from separate storage because it '
        'exceeds the host’s per-file limit, and its `url` in `sources.json` is '
        'absolute.',
    ]

    with open(os.path.join(PUB, 'llms.txt'), 'w') as fh:
        fh.write('\n'.join(lines) + '\n')

    print(f'wrote {os.path.relpath(os.path.join(PUB, "llms.txt"), ROOT)}')
    for name, _, size in published:
        print(f'  data/{name:<28}{size / 1e6:>7.1f}MB')


if __name__ == '__main__':
    main()
